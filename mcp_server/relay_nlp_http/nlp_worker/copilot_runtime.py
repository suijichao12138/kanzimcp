"""Configuration and GitHub Copilot SDK session runtime."""

from __future__ import annotations

import asyncio
import base64
import binascii
import contextlib
import fnmatch
import hashlib
import json
import logging
import os
import re
import sys
import time
import uuid
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import unquote, urlparse

import httpx
import yaml
from copilot import CopilotClient, ModelInfo, RuntimeConnection, ToolInvocation, define_tool
from copilot._jsonrpc import JsonRpcError, ProcessExitedError
from copilot.generated.session_events import (
    AssistantMessageData,
    SessionErrorData,
    SessionIdleData,
)
from copilot.rpc import (
    PermissionDecisionApproveOnce,
    PermissionDecisionReject,
    PermissionDecisionUserNotAvailable,
)
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from session_store import SessionStore

log = logging.getLogger(__name__)
_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_WINDOWS_RUNTIME_NAME = "copilot.exe"


class BridgeError(Exception):
    """Failure safe to report to the user."""


class ConfigError(BridgeError):
    """Configuration is invalid."""


class CopilotRuntimeError(BridgeError):
    """Copilot SDK operation failed."""


def application_directory() -> Path:
    """Return the folder containing the source entry point or frozen executable."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundle_directory() -> Path:
    """Return PyInstaller's resource directory, or the source directory."""
    return Path(getattr(sys, "_MEIPASS", application_directory())).resolve()


def bundled_runtime_path() -> Path | None:
    """Locate the runtime shipped in the Windows portable build."""
    if not getattr(sys, "frozen", False):
        return None
    path = bundle_directory() / "runtime" / _WINDOWS_RUNTIME_NAME
    if not path.is_file():
        raise ConfigError(
            f"bundled Copilot Runtime not found: {path}; "
            "rebuild or re-extract the complete portable folder"
        )
    return path


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class RelayIdentityConfig(StrictModel):
    mode: Literal["dedicated_channel", "message_fields"] = "dedicated_channel"
    dedicated_principal_id: str | None = None
    include_thread_scope: bool = True

    @model_validator(mode="after")
    def validate_identity(self) -> RelayIdentityConfig:
        if self.mode == "dedicated_channel" and not self.dedicated_principal_id:
            raise ValueError("dedicated_principal_id is required for legacy protocol")
        if self.mode == "message_fields" and self.dedicated_principal_id is not None:
            raise ValueError("dedicated_principal_id requires mode=dedicated_channel")
        return self


class RelayConfig(StrictModel):
    url: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    role: Literal["nlp_worker"] = "nlp_worker"
    reconnect_delay_seconds: Annotated[float, Field(gt=0, le=300)] = 3
    ping_interval_seconds: Annotated[float, Field(gt=0, le=300)] = 30
    ping_timeout_seconds: Annotated[float, Field(gt=0, le=300)] = 10
    max_message_bytes: Annotated[int, Field(ge=1024)] = 16 * 1024 * 1024
    allowed_channels: set[str] = Field(default_factory=set)
    identity: RelayIdentityConfig

    @model_validator(mode="after")
    def validate_relay(self) -> RelayConfig:
        parsed = urlparse(self.url)
        if parsed.scheme not in {"ws", "wss"} or not parsed.netloc:
            raise ValueError("relay.url must be a ws:// or wss:// URL")
        path_channel = parsed.path.strip("/").rsplit("/", 1)[-1]
        if path_channel != self.channel:
            raise ValueError(
                f"relay.channel={self.channel!r} does not match URL path {path_channel!r}"
            )
        if not self.allowed_channels or self.channel not in self.allowed_channels:
            raise ValueError("relay.channel must be listed in relay.allowed_channels")
        return self


class ProviderConfig(StrictModel):
    type: Literal["github", "openai", "azure", "anthropic"] = "github"
    base_url: str | None = None
    api_key: str | None = None
    bearer_token: str | None = None
    wire_api: Literal["completions", "responses"] | None = None
    transport: Literal["http", "websockets"] | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    model_id: str | None = None
    wire_model: str | None = None
    max_prompt_tokens: Annotated[int | None, Field(gt=0)] = None
    max_output_tokens: Annotated[int | None, Field(gt=0)] = None
    azure_api_version: str | None = None

    @model_validator(mode="after")
    def validate_byok(self) -> ProviderConfig:
        byok_values = (
            self.base_url,
            self.api_key,
            self.bearer_token,
            self.wire_api,
            self.transport,
            self.model_id,
            self.wire_model,
            self.max_prompt_tokens,
            self.max_output_tokens,
            self.azure_api_version,
        )
        if self.type == "github":
            if self.headers or any(value is not None for value in byok_values):
                raise ValueError("provider.type=github cannot contain BYOK fields")
            return self
        if not self.base_url:
            raise ValueError(f"provider.base_url is required for {self.type} BYOK")
        if self.type != "azure" and self.azure_api_version is not None:
            raise ValueError("azure_api_version is only valid for provider.type=azure")
        return self

    def to_sdk(self) -> dict[str, object] | None:
        if self.type == "github":
            return None
        result: dict[str, object] = {"type": self.type, "base_url": self.base_url}
        optional = {
            "api_key": self.api_key,
            "bearer_token": self.bearer_token,
            "wire_api": self.wire_api,
            "transport": self.transport,
            "model_id": self.model_id,
            "wire_model": self.wire_model,
            "max_prompt_tokens": self.max_prompt_tokens,
            "max_output_tokens": self.max_output_tokens,
        }
        result.update({key: value for key, value in optional.items() if value is not None})
        if self.headers:
            result["headers"] = self.headers
        if self.azure_api_version:
            result["azure"] = {"api_version": self.azure_api_version}
        return result


class ModelConfig(StrictModel):
    name: str = Field(min_length=1)
    reasoning_effort: Literal["low", "medium", "high", "xhigh", "max"] | None = None
    provider: ProviderConfig = Field(default_factory=ProviderConfig)


class LargeOutputConfig(StrictModel):
    enabled: bool = False
    max_size_bytes: Annotated[int, Field(ge=1024)] = 50 * 1024
    output_directory: Path | None = None


class AgentConfig(StrictModel):
    system_prompt: str = ""
    system_prompt_mode: Literal["append", "replace"] = "append"
    available_tools: list[str] = Field(default_factory=list)
    excluded_tools: list[str] = Field(default_factory=list)


class PermissionConfig(StrictModel):
    default: Literal["allow", "deny", "ask"] = "deny"
    allow: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)
    ask: list[str] = Field(default_factory=list)


class CopilotConfig(StrictModel):
    github_token: str | None = None
    use_logged_in_user: bool = True
    working_directory: Path = Path(".")
    base_directory: Path | None = None
    response_timeout_seconds: Annotated[int, Field(ge=1, le=36_000)] = 600
    # 活动刷新式超时阈值(秒): 只要 copilot 还在持续输出/调 MCP就续期,
    # 只有超过 max_idle_seconds 无任何事件才判定真正死寂并超时。
    max_idle_seconds: Annotated[int, Field(ge=1, le=36_000)] = 300
    resume_failure: Literal["error", "new"] = "error"
    configuration_change: Literal["error", "new"] = "error"
    enable_session_store: bool = True
    large_output: LargeOutputConfig = Field(default_factory=LargeOutputConfig)
    model: ModelConfig
    agent: AgentConfig = Field(default_factory=AgentConfig)
    permissions: PermissionConfig = Field(default_factory=PermissionConfig)

    @model_validator(mode="after")
    def validate_auth(self) -> CopilotConfig:
        if not self.github_token and not self.use_logged_in_user:
            raise ValueError("github_token is required when use_logged_in_user=false")
        return self


class SkillEntry(StrictModel):
    path: Path
    enabled: bool = True
    recursive: bool = False


class SkillsConfig(StrictModel):
    max_file_bytes: Annotated[int, Field(ge=1)] = 128 * 1024
    max_total_bytes: Annotated[int, Field(ge=1)] = 512 * 1024
    entries: list[SkillEntry] = Field(default_factory=list)


class MCPBase(StrictModel):
    enabled: bool = True
    tools: list[str] = Field(default_factory=lambda: ["*"])
    timeout_seconds: Annotated[int, Field(ge=1, le=3600)] = 30


class MCPStdioConfig(MCPBase):
    type: Literal["local", "stdio"]
    command: str = Field(min_length=1)
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: Path | None = None


class MCPRemoteConfig(MCPBase):
    type: Literal["http", "sse"]
    url: str = Field(min_length=1)
    headers: dict[str, str] = Field(default_factory=dict)


MCPServerConfig = Annotated[MCPStdioConfig | MCPRemoteConfig, Field(discriminator="type")]


class CompatibilityConfig(StrictModel):
    thinking_text: str = "🤖 Copilot 思考中..."
    output_type: Literal["claude_output"] = "claude_output"
    support_file_download_marker: bool = True
    bridge_http: str | None = None
    bridge_target_open_id: str | None = None
    download_timeout_seconds: Annotated[float, Field(gt=0, le=600)] = 120
    max_upload_bytes: Annotated[int, Field(ge=1)] = 20 * 1024 * 1024
    upload_allowed_roots: list[Path] = Field(default_factory=list)


class ArtifactConfig(StrictModel):
    enabled: bool = False
    allowed_origins: list[str] = Field(default_factory=list)
    timeout_seconds: Annotated[float, Field(gt=0, le=600)] = 60
    max_download_bytes: Annotated[int, Field(ge=1024)] = 64 * 1024 * 1024
    max_tool_output_chars: Annotated[int, Field(ge=256, le=100_000)] = 8_000
    max_search_results: Annotated[int, Field(ge=1, le=1_000)] = 50
    allowed_mime_types: set[
        Literal[
            "application/json",
            "text/plain",
            "image/png",
            "image/jpeg",
            "image/svg+xml",
            "application/octet-stream",
        ]
    ] = Field(
        default_factory=lambda: {
            "application/json",
            "text/plain",
            "image/png",
            "image/jpeg",
            "image/svg+xml",
            "application/octet-stream",
        }
    )

    @model_validator(mode="after")
    def validate_download_policy(self) -> ArtifactConfig:
        if self.enabled and not self.allowed_origins:
            raise ValueError("artifacts.allowed_origins is required when artifacts.enabled=true")
        for origin in self.allowed_origins:
            parsed = urlparse(origin)
            try:
                port = parsed.port
            except ValueError as exc:
                raise ValueError(f"invalid artifacts.allowed_origins entry: {origin}") from exc
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
                or parsed.path not in {"", "/"}
                or port is None
            ):
                raise ValueError(
                    "artifacts.allowed_origins entries must be explicit "
                    f"http(s)://host:port origins: {origin}"
                )
        return self


class MessageConfig(StrictModel):
    max_input_chars: Annotated[int, Field(ge=1, le=100_000)] = 12_000
    max_output_chars: Annotated[int, Field(ge=100, le=100_000)] = 3_500
    queue_size: Annotated[int, Field(ge=1, le=10_000)] = 256
    worker_count: Annotated[int, Field(ge=1, le=32)] = 1
    dedup_ttl_seconds: Annotated[int, Field(ge=60)] = 86_400


class StorageConfig(StrictModel):
    database_path: Path = Path("./data/bridge.db")


class LoggingConfig(StrictModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    file: Path | None = Path("./logs/bridge.log")
    max_bytes: Annotated[int, Field(ge=1024)] = 10 * 1024 * 1024
    backup_count: Annotated[int, Field(ge=0, le=100)] = 5


class AppConfig(StrictModel):
    relay: RelayConfig
    copilot: CopilotConfig
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict)
    artifacts: ArtifactConfig = Field(default_factory=ArtifactConfig)
    compatibility: CompatibilityConfig = Field(default_factory=CompatibilityConfig)
    messages: MessageConfig = Field(default_factory=MessageConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    config_dir: Path = Field(default=Path("."), exclude=True)

    @model_validator(mode="after")
    def validate_legacy_concurrency(self) -> AppConfig:
        if (
            self.relay.identity.mode == "dedicated_channel"
            and self.messages.worker_count != 1
        ):
            raise ValueError("worker_count must be 1 with dedicated_channel routing")
        return self

    def resolve_paths(self) -> AppConfig:
        base = self.config_dir
        self.copilot.working_directory = _resolve(base, self.copilot.working_directory)
        if self.copilot.base_directory:
            self.copilot.base_directory = _resolve(base, self.copilot.base_directory)
        if self.copilot.large_output.output_directory:
            self.copilot.large_output.output_directory = _resolve(
                base, self.copilot.large_output.output_directory
            )
        elif self.copilot.base_directory:
            self.copilot.large_output.output_directory = (
                self.copilot.base_directory
                / "session-state"
                / "{session_id}"
                / "files"
            )
        self.storage.database_path = _resolve(base, self.storage.database_path)
        if self.logging.file:
            self.logging.file = _resolve(base, self.logging.file)
        self.compatibility.upload_allowed_roots = [
            _resolve(base, root) for root in self.compatibility.upload_allowed_roots
        ]
        for entry in self.skills.entries:
            entry.path = _resolve(base, entry.path)
        for server in self.mcp_servers.values():
            if isinstance(server, MCPStdioConfig) and server.cwd:
                server.cwd = _resolve(base, server.cwd)
        return self

    def validate_runtime_paths(self) -> AppConfig:
        _require_directory(
            self.copilot.working_directory,
            "copilot.working_directory",
        )
        for name, server in self.mcp_servers.items():
            if server.enabled and isinstance(server, MCPStdioConfig) and server.cwd:
                _require_directory(server.cwd, f"mcp_servers.{name}.cwd")
        for index, root in enumerate(self.compatibility.upload_allowed_roots):
            _require_directory(root, f"compatibility.upload_allowed_roots.{index}")
        if self.artifacts.enabled and not self.copilot.base_directory:
            raise ConfigError(
                "copilot.base_directory is required when artifacts.enabled=true"
            )
        large_output = self.copilot.large_output
        if large_output.enabled:
            if not self.copilot.base_directory:
                raise ConfigError(
                    "copilot.base_directory is required when copilot.large_output.enabled=true"
                )
            if not large_output.output_directory:
                raise ConfigError("copilot.large_output.output_directory is required")
            expected = (
                self.copilot.base_directory
                / "session-state"
                / "{session_id}"
                / "files"
            )
            if os.path.normcase(str(large_output.output_directory)) != os.path.normcase(
                str(expected)
            ):
                raise ConfigError(
                    "copilot.large_output.output_directory must be "
                    f"{expected} so output stays isolated per session"
                )
        return self


def _resolve(base: Path, value: Path) -> Path:
    return value if value.is_absolute() else (base / value).resolve()


def _require_directory(path: Path, field: str) -> None:
    if not path.exists():
        raise ConfigError(f"{field} does not exist: {path}")
    if not path.is_dir():
        raise ConfigError(f"{field} is not a directory: {path}")


def _expand_env(value: object, location: str = "config") -> object:
    if isinstance(value, str):
        missing: set[str] = set()

        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            resolved = os.environ.get(name)
            if resolved is None:
                missing.add(name)
                return match.group(0)
            return resolved

        expanded = _ENV_PATTERN.sub(replace, value)
        if missing:
            raise ConfigError(
                f"{location} references unset environment variables: "
                f"{', '.join(sorted(missing))}"
            )
        return expanded
    if isinstance(value, list):
        return [_expand_env(item, f"{location}[]") for item in value]
    if isinstance(value, dict):
        return {key: _expand_env(item, f"{location}.{key}") for key, item in value.items()}
    return value


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path).resolve()
    load_dotenv(config_path.parent / ".env", override=False)
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"configuration file not found: {config_path}") from exc
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ConfigError(f"cannot read configuration {config_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("configuration root must be a YAML mapping")
    expanded = _expand_env(raw)
    if not isinstance(expanded, dict):
        raise ConfigError("configuration root must remain a mapping")
    try:
        return AppConfig.model_validate(
            {**expanded, "config_dir": config_path.parent}
        ).resolve_paths().validate_runtime_paths()
    except ValidationError as exc:
        raise ConfigError(f"invalid configuration:\n{exc}") from exc


def _walk_skill_files(root: Path) -> list[Path]:
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as exc:
        raise ConfigError(f"cannot inspect skill directory {root}: {exc}") from exc

    found: list[Path] = []

    def walk_error(error: OSError) -> None:
        raise ConfigError(f"cannot scan skill directory {resolved_root}: {error}")

    for current, directories, files in os.walk(
        resolved_root,
        topdown=True,
        onerror=walk_error,
        followlinks=False,
    ):
        current_path = Path(current)
        directories[:] = sorted(
            (
                name
                for name in directories
                if not (current_path / name).is_symlink()
            ),
            key=str.casefold,
        )
        for name in sorted(files, key=str.casefold):
            if name.casefold() != "skill.md":
                continue
            candidate = current_path / name
            try:
                resolved = candidate.resolve(strict=True)
            except OSError as exc:
                raise ConfigError(f"cannot inspect skill {candidate}: {exc}") from exc
            if not resolved.is_relative_to(resolved_root):
                raise ConfigError(f"skill symlink escapes configured directory: {candidate}")
            if resolved.is_file():
                found.append(resolved)
    return found


def _discover_skill_files(entry: SkillEntry) -> list[Path]:
    path = entry.path
    if not path.exists():
        raise ConfigError(f"configured skill does not exist: {path}")
    if path.is_file():
        if path.name.casefold() != "skill.md":
            raise ConfigError(f"skill file must be named SKILL.md: {path}")
        return [path.resolve()]
    if not path.is_dir():
        raise ConfigError(f"skill path is not a file or directory: {path}")

    direct = path / "SKILL.md"
    if direct.is_file() and not entry.recursive:
        resolved_root = path.resolve()
        resolved_direct = direct.resolve()
        if not resolved_direct.is_relative_to(resolved_root):
            raise ConfigError(f"skill symlink escapes configured directory: {direct}")
        return [resolved_direct]
    found = _walk_skill_files(path)
    if not found:
        raise ConfigError(f"configured skill directory contains no SKILL.md: {path}")
    return found


def load_skills(config: SkillsConfig) -> str:
    discovered: dict[str, Path] = {}
    for entry in config.entries:
        if not entry.enabled:
            continue
        for path in _discover_skill_files(entry):
            key = os.path.normcase(str(path.resolve()))
            discovered.setdefault(key, path)

    blocks: list[str] = []
    total = 0
    paths = sorted(discovered.values(), key=lambda path: path.as_posix().casefold())
    for path in paths:
        try:
            size = path.stat().st_size
        except FileNotFoundError as exc:
            raise ConfigError(f"configured skill does not exist: {path}") from exc
        except OSError as exc:
            raise ConfigError(f"cannot inspect skill {path}: {exc}") from exc
        if size > config.max_file_bytes:
            raise ConfigError(f"skill exceeds max_file_bytes: {path}")
        total += size
        if total > config.max_total_bytes:
            raise ConfigError("enabled skills exceed max_total_bytes")
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ConfigError(f"cannot read UTF-8 skill {path}: {exc}") from exc
        blocks.append(f"<skill source={path.as_posix()!r}>\n{content.strip()}\n</skill>")
    return "\n\n".join(blocks)


def validate_runtime_config(config: AppConfig) -> Path | None:
    """Validate SDK, skill files, and the frozen runtime without opening the network."""
    config.validate_runtime_paths()
    CopilotRuntime.validate_sdk_version()
    load_skills(config.skills)
    return bundled_runtime_path()


def _client_options(config: AppConfig) -> dict[str, Any]:
    cfg = config.copilot
    options: dict[str, Any] = {
        "working_directory": str(cfg.working_directory),
        "github_token": cfg.github_token,
        "use_logged_in_user": cfg.use_logged_in_user,
        "base_directory": str(cfg.base_directory) if cfg.base_directory else None,
        "log_level": "warning",
    }
    if runtime_path := bundled_runtime_path():
        options["connection"] = RuntimeConnection.for_stdio(path=str(runtime_path))
    return options


def _config_secrets(config: AppConfig) -> list[str]:
    provider = config.copilot.model.provider
    return [
        value
        for value in (
            config.copilot.github_token,
            provider.api_key,
            provider.bearer_token,
            *(
                value
                for server in config.mcp_servers.values()
                for value in getattr(server, "headers", {}).values()
            ),
            *provider.headers.values(),
        )
        if value
    ]


def _safe_config_error(config: AppConfig, error: BaseException) -> str:
    rendered = str(error)
    for secret in _config_secrets(config):
        rendered = rendered.replace(secret, "******")
    return rendered


async def list_available_models(config: AppConfig) -> list[ModelInfo]:
    """List models through the configured SDK runtime without creating a session."""
    validate_runtime_config(config)
    client = CopilotClient(**_client_options(config))
    started = False
    try:
        started = True
        await client.start()
        return await client.list_models()
    except (
        JsonRpcError,
        ProcessExitedError,
        OSError,
        RuntimeError,
        ValueError,
        TimeoutError,
    ) as exc:
        raise CopilotRuntimeError(
            "failed to list Copilot models; check GitHub authorization and network: "
            f"{_safe_config_error(config, exc)}"
        ) from exc
    finally:
        if started:
            try:
                await client.stop()
            except (OSError, RuntimeError) as exc:
                log.warning(
                    "Failed to stop Copilot Runtime after listing models: %s",
                    _safe_config_error(config, exc),
                )


def convert_mcp_servers(
    servers: dict[str, MCPServerConfig],
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for name, server in servers.items():
        if not server.enabled:
            continue
        converted: dict[str, object] = {
            "type": server.type,
            "tools": server.tools,
            "timeout": server.timeout_seconds * 1000,
        }
        if isinstance(server, MCPStdioConfig):
            converted["command"] = server.command
            if server.args:
                converted["args"] = server.args
            if server.env:
                converted["env"] = server.env
            if server.cwd:
                converted["working_directory"] = str(server.cwd)
        else:
            converted["url"] = server.url
            if server.headers:
                converted["headers"] = server.headers
        result[name] = converted
    return result


def build_permission_handler(config: PermissionConfig):
    def matches(name: str, patterns: list[str]) -> bool:
        return any(fnmatch.fnmatchcase(name.lower(), pattern.lower()) for pattern in patterns)

    def decide(request: object, _invocation: Any) -> object:
        name = getattr(request, "tool_name", None) or getattr(request, "kind", None)
        name = name if isinstance(name, str) else type(request).__name__
        if getattr(request, "managed_approval_required", False) is True:
            return PermissionDecisionUserNotAvailable()
        if matches(name, config.deny):
            decision = "deny"
        elif matches(name, config.allow):
            decision = "allow"
        elif matches(name, config.ask):
            decision = "ask"
        else:
            decision = config.default
        if decision == "allow":
            return PermissionDecisionApproveOnce()
        if decision == "ask":
            log.warning("No safe Feishu approval UI; rejecting ask permission for %s", name)
            return PermissionDecisionUserNotAvailable()
        return PermissionDecisionReject(feedback=f"Tool {name!r} denied by bridge policy")

    return decide


class ArtifactError(CopilotRuntimeError):
    """A remote artifact failed a configured safety check."""


class DownloadArtifactParams(StrictModel):
    url: str = Field(min_length=1)
    filename: str | None = None


class ReadArtifactParams(StrictModel):
    path: str = Field(min_length=1)
    offset_bytes: Annotated[int, Field(ge=0)] = 0
    max_chars: Annotated[int | None, Field(ge=1)] = None


class SearchArtifactParams(StrictModel):
    path: str = Field(min_length=1)
    keyword: str = Field(min_length=1, max_length=1_000)
    case_sensitive: bool = False
    max_results: Annotated[int | None, Field(ge=1)] = None


class QueryJsonParams(StrictModel):
    path: str = Field(min_length=1)
    json_path: str = Field(default="$", min_length=1, max_length=2_000)
    max_chars: Annotated[int | None, Field(ge=1)] = None


class MaterializeImageParams(StrictModel):
    url: str | None = None
    source_path: str | None = None
    json_path: str | None = None
    filename: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> MaterializeImageParams:
        if bool(self.url) == bool(self.source_path):
            raise ValueError("provide exactly one of url or source_path")
        if self.source_path and not self.json_path:
            raise ValueError("json_path is required with source_path")
        if self.url and self.json_path:
            raise ValueError("json_path is only valid with source_path")
        return self


_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SVG_PATTERN = re.compile(
    rb"^\s*(?:<\?xml[^>]*>\s*)?(?:<!--.*?-->\s*)*<svg(?:\s|>)",
    re.IGNORECASE | re.DOTALL,
)
_JSON_PATH_PATTERN = re.compile(r"(?:^|\.)([A-Za-z_][A-Za-z0-9_-]*)|\[(\d+)\]")
_MIME_EXTENSIONS = {
    "application/json": ".json",
    "text/plain": ".txt",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/svg+xml": ".svg",
}
_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/svg+xml"}


def _session_files_directory(config: AppConfig, session_id: str) -> Path:
    if not _SESSION_ID_PATTERN.fullmatch(session_id):
        raise ArtifactError("Copilot session ID is not safe for a filesystem path")
    base_directory = config.copilot.base_directory
    if not base_directory:
        raise ArtifactError("copilot.base_directory is required for session files")
    session_state = (base_directory / "session-state").resolve()
    session_state.mkdir(parents=True, exist_ok=True)
    directory = session_state / session_id / "files"
    directory.mkdir(parents=True, exist_ok=True)
    resolved = directory.resolve()
    expected_parent = session_state / session_id
    if (
        not resolved.is_relative_to(session_state)
        or os.path.normcase(str(resolved.parent)) != os.path.normcase(str(expected_parent))
        or resolved.name.casefold() != "files"
    ):
        raise ArtifactError("session files directory escapes copilot.base_directory")
    return resolved


def _bounded_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    suffix = f"\n...[truncated; total_chars={len(text)}]"
    return text[: max(0, limit - len(suffix))] + suffix


def _json_path_tokens(path: str) -> list[str | int]:
    source = path.strip()
    if source == "$":
        return []
    if source.startswith("$"):
        source = source[1:]
    if source.startswith("."):
        source = source[1:]
    tokens: list[str | int] = []
    position = 0
    while position < len(source):
        match = _JSON_PATH_PATTERN.match(source, position)
        if not match:
            raise ArtifactError(
                "json_path supports only dot keys and numeric indexes, for example "
                "$.items[0].name"
            )
        key, index = match.groups()
        tokens.append(key if key is not None else int(index))
        position = match.end()
    return tokens


def _select_json_value(document: object, path: str) -> object:
    current = document
    for token in _json_path_tokens(path):
        if isinstance(token, int):
            if not isinstance(current, list) or token >= len(current):
                raise ArtifactError(f"JSON path index not found: {token}")
            current = current[token]
        else:
            if not isinstance(current, dict) or token not in current:
                raise ArtifactError(f"JSON path key not found: {token}")
            current = current[token]
    return current


def _canonical_declared_mime(content_type: str) -> str:
    mime = content_type.partition(";")[0].strip().casefold()
    if mime.endswith("+json") or mime == "text/json":
        return "application/json"
    if mime == "image/jpg":
        return "image/jpeg"
    if mime in {"application/xml", "text/xml"}:
        return "image/svg+xml"
    return mime


def _detect_file_mime(path: Path) -> str:
    with path.open("rb") as source:
        head = source.read(8192)
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if _SVG_PATTERN.match(head):
        try:
            with path.open("r", encoding="utf-8-sig") as source:
                while source.read(64 * 1024):
                    pass
        except (OSError, UnicodeError) as exc:
            raise ArtifactError("downloaded SVG is not valid UTF-8") from exc
        return "image/svg+xml"
    stripped = head.removeprefix(b"\xef\xbb\xbf").lstrip()
    if stripped.startswith((b"{", b"[")):
        try:
            with path.open("r", encoding="utf-8-sig") as source:
                json.load(source)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ArtifactError("downloaded JSON is not valid UTF-8 JSON") from exc
        return "application/json"
    if b"\x00" in head:
        raise ArtifactError("downloaded file has an unsupported binary format")
    try:
        with path.open("r", encoding="utf-8-sig") as source:
            while source.read(64 * 1024):
                pass
    except (OSError, UnicodeError) as exc:
        raise ArtifactError("downloaded text is not UTF-8") from exc
    return "text/plain"


class ArtifactManager:
    """Session-isolated downloads and bounded inspection tools for remote MCP output."""

    TOOL_NAMES = (
        "artifact_download",
        "artifact_read",
        "artifact_search",
        "artifact_json_query",
        "artifact_materialize_image",
    )

    def __init__(
        self,
        config: AppConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self.policy = config.artifacts
        self._transport = transport
        self._origins = {
            self._url_origin(url) for url in self.policy.allowed_origins
        }

    @staticmethod
    def _url_origin(url: str) -> tuple[str, str, int]:
        parsed = urlparse(url)
        try:
            port = parsed.port
        except ValueError as exc:
            raise ArtifactError("download URL has an invalid port") from exc
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
            or port is None
        ):
            raise ArtifactError("download URL must be an explicit http(s)://host:port URL")
        return parsed.scheme, parsed.hostname.casefold(), port

    def _validate_url(self, url: str) -> tuple[str, str, int]:
        origin = self._url_origin(url)
        if origin not in self._origins:
            rendered = f"{origin[0]}://{origin[1]}:{origin[2]}"
            raise ArtifactError(f"download URL origin is not allowed: {rendered}")
        return origin

    def _validate_session_file(self, session_id: str, path_value: str) -> Path:
        root = _session_files_directory(self.config, session_id)
        candidate = Path(path_value)
        if not candidate.is_absolute():
            candidate = root / candidate
        try:
            path = candidate.resolve(strict=True)
        except OSError as exc:
            raise ArtifactError(f"artifact file does not exist: {candidate}") from exc
        if not path.is_relative_to(root):
            raise ArtifactError("artifact path is outside the current session files directory")
        try:
            if not path.is_file():
                raise ArtifactError("artifact path is not a regular file")
        except OSError as exc:
            raise ArtifactError(f"cannot inspect artifact file: {path}") from exc
        return path

    @staticmethod
    def _safe_filename(raw_name: str | None, url: str, extension: str) -> str:
        source = raw_name or Path(unquote(urlparse(url).path)).name or "artifact"
        stem = re.sub(r"[^\w.-]", "_", Path(source).stem, flags=re.UNICODE)
        stem = stem.strip("._")[:80] or "artifact"
        return f"{stem}{extension}"

    @staticmethod
    def _unique_destination(root: Path, filename: str) -> Path:
        candidate = root / filename
        counter = 1
        while candidate.exists():
            candidate = root / f"{Path(filename).stem}-{counter}{Path(filename).suffix}"
            counter += 1
        return candidate

    def _validate_detected_mime(self, declared: str, detected: str) -> None:
        canonical = _canonical_declared_mime(declared)
        if not canonical:
            raise ArtifactError("download response has no Content-Type")
        if canonical not in self.policy.allowed_mime_types:
            raise ArtifactError(f"download Content-Type is not allowed: {canonical}")
        if detected not in self.policy.allowed_mime_types:
            raise ArtifactError(f"detected file type is not allowed: {detected}")
        compatible = (
            canonical == detected
            or canonical == "application/octet-stream"
            or (canonical == "text/plain" and detected in {"application/json", "image/svg+xml"})
        )
        if not compatible:
            raise ArtifactError(
                f"download MIME mismatch: declared {canonical}, detected {detected}"
            )

    async def download_url(
        self,
        session_id: str,
        url: str,
        filename: str | None = None,
        *,
        require_image: bool = False,
    ) -> tuple[Path, str, int]:
        if not self.policy.enabled:
            raise ArtifactError("remote artifact tools are disabled")
        origin = self._validate_url(url)
        root = _session_files_directory(self.config, session_id)
        temporary = root / f".download-{uuid.uuid4().hex}.part"
        total = 0
        declared = ""
        try:
            timeout = httpx.Timeout(self.policy.timeout_seconds)
            async with (
                httpx.AsyncClient(
                    timeout=timeout,
                    follow_redirects=False,
                    transport=self._transport,
                ) as client,
                client.stream("GET", url) as response,
            ):
                if 300 <= response.status_code < 400:
                    raise ArtifactError("download redirects are not allowed")
                if response.status_code >= 400:
                    raise ArtifactError(
                        f"download failed with HTTP {response.status_code} from "
                        f"{origin[0]}://{origin[1]}:{origin[2]}"
                    )
                declared = response.headers.get("content-type", "")
                content_length = response.headers.get("content-length")
                if content_length:
                    try:
                        declared_size = int(content_length)
                    except ValueError as exc:
                        raise ArtifactError("download Content-Length is invalid") from exc
                    if declared_size > self.policy.max_download_bytes:
                        raise ArtifactError("download exceeds artifacts.max_download_bytes")
                with temporary.open("xb") as output:
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > self.policy.max_download_bytes:
                            raise ArtifactError(
                                "download exceeds artifacts.max_download_bytes"
                            )
                        output.write(chunk)
                    output.flush()
                    os.fsync(output.fileno())
            detected = _detect_file_mime(temporary)
            self._validate_detected_mime(declared, detected)
            if require_image and detected not in _IMAGE_MIME_TYPES:
                raise ArtifactError("downloaded artifact is not a supported image")
            destination = self._unique_destination(
                root,
                self._safe_filename(filename, url, _MIME_EXTENSIONS[detected]),
            )
            os.replace(temporary, destination)
            return destination.resolve(), detected, total
        except httpx.TimeoutException as exc:
            raise ArtifactError("artifact download timed out") from exc
        except httpx.RequestError as exc:
            raise ArtifactError(
                f"artifact download failed for {origin[0]}://{origin[1]}:{origin[2]}"
            ) from exc
        finally:
            temporary.unlink(missing_ok=True)

    def _limit(self, requested: int | None) -> int:
        return min(
            requested or self.policy.max_tool_output_chars,
            self.policy.max_tool_output_chars,
        )

    def read_text(
        self,
        session_id: str,
        path_value: str,
        offset_bytes: int = 0,
        max_chars: int | None = None,
    ) -> str:
        path = self._validate_session_file(session_id, path_value)
        limit = self._limit(max_chars)
        with path.open("rb") as source:
            source.seek(offset_bytes)
            data = source.read(limit * 4 + 4)
        if b"\x00" in data:
            raise ArtifactError("artifact_read supports UTF-8 text files only")
        text = data.decode("utf-8", errors="replace")
        rendered = (
            f"path={path}\noffset_bytes={offset_bytes}\n"
            f"next_offset_bytes={offset_bytes + len(data)}\n{text}"
        )
        return _bounded_text(rendered, limit)

    def search_text(
        self,
        session_id: str,
        path_value: str,
        keyword: str,
        *,
        case_sensitive: bool = False,
        max_results: int | None = None,
    ) -> str:
        path = self._validate_session_file(session_id, path_value)
        result_limit = min(
            max_results or self.policy.max_search_results,
            self.policy.max_search_results,
        )
        needle = keyword if case_sensitive else keyword.casefold()
        overlap = max(len(keyword) - 1, 0)
        offset = 0
        tail = ""
        results: list[str] = []
        with path.open("r", encoding="utf-8", errors="replace") as source:
            while len(results) < result_limit:
                chunk = source.read(64 * 1024)
                if not chunk:
                    break
                combined = tail + chunk
                haystack = combined if case_sensitive else combined.casefold()
                start = 0
                while len(results) < result_limit:
                    match_at = haystack.find(needle, start)
                    if match_at < 0:
                        break
                    snippet_start = max(0, match_at - 80)
                    snippet_end = min(len(combined), match_at + len(keyword) + 80)
                    snippet = combined[snippet_start:snippet_end].replace("\r", " ").replace(
                        "\n", " "
                    )
                    absolute = max(0, offset - len(tail) + match_at)
                    results.append(f"offset_chars={absolute}: {snippet}")
                    start = match_at + max(1, len(keyword))
                offset += len(chunk)
                tail = combined[-overlap:] if overlap else ""
        rendered = (
            f"path={path}\nkeyword={keyword!r}\nmatches_returned={len(results)}\n"
            + ("\n".join(results) if results else "(no matches)")
        )
        return _bounded_text(rendered, self.policy.max_tool_output_chars)

    def query_json(
        self,
        session_id: str,
        path_value: str,
        json_path: str,
        max_chars: int | None = None,
    ) -> str:
        path = self._validate_session_file(session_id, path_value)
        if path.stat().st_size > self.policy.max_download_bytes:
            raise ArtifactError("JSON exceeds artifacts.max_download_bytes")
        try:
            with path.open("r", encoding="utf-8-sig") as source:
                document = json.load(source)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ArtifactError("artifact is not valid UTF-8 JSON") from exc
        selected = _select_json_value(document, json_path)
        rendered = json.dumps(selected, ensure_ascii=False, separators=(",", ":"))
        limit = self._limit(max_chars)
        return _bounded_text(
            f"path={path}\njson_path={json_path}\n{rendered}",
            limit,
        )

    def _write_image(
        self,
        session_id: str,
        data: bytes,
        filename: str | None,
    ) -> tuple[Path, str, int]:
        if len(data) > self.policy.max_download_bytes:
            raise ArtifactError("image exceeds artifacts.max_download_bytes")
        root = _session_files_directory(self.config, session_id)
        temporary = root / f".image-{uuid.uuid4().hex}.part"
        try:
            with temporary.open("xb") as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            detected = _detect_file_mime(temporary)
            if detected not in _IMAGE_MIME_TYPES:
                raise ArtifactError("JSON field is not a supported PNG, JPEG, or SVG image")
            destination = self._unique_destination(
                root,
                self._safe_filename(filename, "http://local/image", _MIME_EXTENSIONS[detected]),
            )
            os.replace(temporary, destination)
            return destination.resolve(), detected, len(data)
        finally:
            temporary.unlink(missing_ok=True)

    async def materialize_image(
        self,
        session_id: str,
        *,
        url: str | None = None,
        source_path: str | None = None,
        json_path: str | None = None,
        filename: str | None = None,
    ) -> tuple[Path, str, int]:
        if url:
            return await self.download_url(
                session_id,
                url,
                filename,
                require_image=True,
            )
        if not source_path or not json_path:
            raise ArtifactError("source_path and json_path are required")
        source = self._validate_session_file(session_id, source_path)
        if source.stat().st_size > self.policy.max_download_bytes:
            raise ArtifactError("JSON exceeds artifacts.max_download_bytes")
        try:
            with source.open("r", encoding="utf-8-sig") as stream:
                value = _select_json_value(json.load(stream), json_path)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ArtifactError("artifact is not valid UTF-8 JSON") from exc
        if not isinstance(value, str):
            raise ArtifactError("selected JSON image field must be a string")
        if value.startswith("http://") or value.startswith("https://"):
            return await self.download_url(
                session_id,
                value,
                filename,
                require_image=True,
            )
        encoded = value
        declared_mime: str | None = None
        if value.startswith("data:"):
            header, separator, encoded = value.partition(",")
            if not separator or not header.casefold().endswith(";base64"):
                raise ArtifactError("image data URL must use base64 encoding")
            declared_mime = header[5:-7].casefold()
            if declared_mime not in _IMAGE_MIME_TYPES:
                raise ArtifactError("image data URL MIME is not supported")
        compact = "".join(encoded.split())
        max_encoded = ((self.policy.max_download_bytes + 2) // 3) * 4
        if len(compact) > max_encoded:
            raise ArtifactError("base64 image exceeds artifacts.max_download_bytes")
        try:
            data = base64.b64decode(compact, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ArtifactError("selected JSON image field is not valid base64") from exc
        result = self._write_image(session_id, data, filename)
        if declared_mime and result[1] != declared_mime:
            result[0].unlink(missing_ok=True)
            raise ArtifactError(
                f"image data URL MIME mismatch: declared {declared_mime}, detected {result[1]}"
            )
        return result

    def build_tools(self) -> list[object]:
        async def download(
            params: DownloadArtifactParams,
            invocation: ToolInvocation,
        ) -> str:
            path, mime, size = await self.download_url(
                invocation.session_id,
                params.url,
                params.filename,
            )
            return _bounded_text(
                f"Downloaded without exposing the body to context.\n"
                f"path={path}\nmime={mime}\nbytes={size}",
                self.policy.max_tool_output_chars,
            )

        def read(params: ReadArtifactParams, invocation: ToolInvocation) -> str:
            return self.read_text(
                invocation.session_id,
                params.path,
                params.offset_bytes,
                params.max_chars,
            )

        def search(params: SearchArtifactParams, invocation: ToolInvocation) -> str:
            return self.search_text(
                invocation.session_id,
                params.path,
                params.keyword,
                case_sensitive=params.case_sensitive,
                max_results=params.max_results,
            )

        def query(params: QueryJsonParams, invocation: ToolInvocation) -> str:
            return self.query_json(
                invocation.session_id,
                params.path,
                params.json_path,
                params.max_chars,
            )

        async def image(
            params: MaterializeImageParams,
            invocation: ToolInvocation,
        ) -> str:
            path, mime, size = await self.materialize_image(
                invocation.session_id,
                url=params.url,
                source_path=params.source_path,
                json_path=params.json_path,
                filename=params.filename,
            )
            return _bounded_text(
                f"Image materialized for Feishu upload.\nmime={mime}\nbytes={size}\n"
                f"[FILE]\npath={path}",
                self.policy.max_tool_output_chars,
            )

        definitions = (
            (
                "artifact_download",
                "Download an allowlisted MCP artifact URL into this Copilot session. "
                "The response body is never returned to model context.",
                download,
                DownloadArtifactParams,
            ),
            (
                "artifact_read",
                "Read a bounded UTF-8 fragment from an artifact in this session.",
                read,
                ReadArtifactParams,
            ),
            (
                "artifact_search",
                "Search an artifact in this session and return bounded snippets.",
                search,
                SearchArtifactParams,
            ),
            (
                "artifact_json_query",
                "Select a value with a simple JSON path such as $.items[0].name.",
                query,
                QueryJsonParams,
            ),
            (
                "artifact_materialize_image",
                "Safely materialize a PNG/JPEG/SVG from an allowlisted URL or a "
                "base64/data URL field in a downloaded JSON artifact.",
                image,
                MaterializeImageParams,
            ),
        )
        return [
            define_tool(
                name,
                description=description,
                handler=handler,
                params_type=params_type,
                skip_permission=True,
                defer="never",
            )
            for name, description, handler, params_type in definitions
        ]


class CopilotRuntime:
    def __init__(self, config: AppConfig, store: SessionStore) -> None:
        self.config = config
        self.store = store
        self.client: CopilotClient | None = None
        self.sessions: dict[str, Any] = {}
        self.locks: dict[str, asyncio.Lock] = {}
        self.artifacts = ArtifactManager(config)
        self._secrets = _config_secrets(config)
        self._session_kwargs = self._build_session_kwargs()
        self.config_fingerprint = self._build_fingerprint()
        self._last_activity = time.time()  # 最近一次 copilot 活动时间(供活动刷新式超时)

    @staticmethod
    def validate_sdk_version() -> None:
        try:
            current = version("github-copilot-sdk")
            parts = tuple(int(part) for part in current.split(".")[:3])
        except PackageNotFoundError as exc:
            raise ConfigError("github-copilot-sdk is not installed") from exc
        except ValueError as exc:
            raise ConfigError("cannot parse github-copilot-sdk version") from exc
        if not ((1, 0, 11) <= parts < (1, 1, 0)):
            raise ConfigError(f"supported SDK range is >=1.0.11,<1.1; installed {current}")

    def _build_session_kwargs(self) -> dict[str, Any]:
        copilot = self.config.copilot
        skills = load_skills(self.config.skills)
        prompt = copilot.agent.system_prompt.strip()
        if skills:
            prompt = (
                f"{prompt}\n\n<configured_skills>\n{skills}\n</configured_skills>"
            ).strip()
        kwargs: dict[str, Any] = {
            "model": copilot.model.name,
            "working_directory": str(copilot.working_directory),
            "mcp_servers": convert_mcp_servers(self.config.mcp_servers),
            "on_permission_request": build_permission_handler(copilot.permissions),
            "enable_session_store": copilot.enable_session_store,
            "streaming": False,
        }
        if copilot.model.reasoning_effort:
            kwargs["reasoning_effort"] = copilot.model.reasoning_effort
        if provider := copilot.model.provider.to_sdk():
            kwargs["provider"] = provider
        if prompt:
            kwargs["system_message"] = {
                "mode": copilot.agent.system_prompt_mode,
                "content": prompt,
            }
        if copilot.agent.available_tools:
            available_tools = list(copilot.agent.available_tools)
            if self.config.artifacts.enabled:
                available_tools.extend(ArtifactManager.TOOL_NAMES)
            kwargs["available_tools"] = list(dict.fromkeys(available_tools))
        if copilot.agent.excluded_tools:
            kwargs["excluded_tools"] = copilot.agent.excluded_tools
        if self.config.artifacts.enabled:
            kwargs["tools"] = self.artifacts.build_tools()
        return kwargs

    def _session_kwargs_for(self, session_id: str) -> dict[str, Any]:
        kwargs = dict(self._session_kwargs)
        large_output = self.config.copilot.large_output
        if large_output.enabled:
            directory = _session_files_directory(self.config, session_id)
            configured = large_output.output_directory
            if not configured:
                raise ConfigError("copilot.large_output.output_directory is required")
            rendered = Path(str(configured).replace("{session_id}", session_id)).resolve()
            if os.path.normcase(str(rendered)) != os.path.normcase(str(directory)):
                raise ConfigError(
                    "copilot.large_output.output_directory did not resolve to the "
                    "current session files directory"
                )
            kwargs["large_output"] = {
                "enabled": True,
                "max_size_bytes": large_output.max_size_bytes,
                "output_directory": str(directory),
            }
        else:
            kwargs["large_output"] = {"enabled": False}
        return kwargs

    def _build_fingerprint(self) -> str:
        copilot = self.config.copilot
        provider = copilot.model.provider
        mcp = {
            name: {
                "config": server.model_dump(exclude={"enabled"}),
                "secret_hash": hashlib.sha256(
                    json.dumps(
                        getattr(server, "headers", {}),
                        sort_keys=True,
                    ).encode()
                ).hexdigest(),
            }
            for name, server in sorted(self.config.mcp_servers.items())
            if server.enabled
        }
        payload = {
            "model": copilot.model.name,
            "reasoning": copilot.model.reasoning_effort,
            "provider": provider.model_dump(
                exclude={"api_key", "bearer_token", "headers"}
            ),
            "provider_secret_hash": hashlib.sha256(
                f"{provider.api_key or ''}\0{provider.bearer_token or ''}\0"
                f"{json.dumps(provider.headers, sort_keys=True)}".encode()
            ).hexdigest(),
            "working_directory": str(copilot.working_directory),
            "system_prompt_hash": hashlib.sha256(
                copilot.agent.system_prompt.encode()
            ).hexdigest(),
            "skills_hash": hashlib.sha256(load_skills(self.config.skills).encode()).hexdigest(),
            "tools": {
                "available": copilot.agent.available_tools,
                "excluded": copilot.agent.excluded_tools,
                "permissions": copilot.permissions.model_dump(),
            },
            "large_output": copilot.large_output.model_dump(),
            "artifacts": self.config.artifacts.model_dump(),
            "mcp": mcp,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()

    def _safe_error(self, error: BaseException) -> str:
        rendered = str(error)
        for secret in self._secrets:
            rendered = rendered.replace(secret, "******")
        return rendered

    def _require_client(self) -> CopilotClient:
        if self.client is None:
            raise CopilotRuntimeError("Copilot SDK client is not started")
        return self.client

    async def start(self) -> None:
        self.config.validate_runtime_paths()
        self.validate_sdk_version()
        try:
            self.client = CopilotClient(**_client_options(self.config))
            await self.client.start()
        except (OSError, RuntimeError, ValueError) as exc:
            self.client = None
            raise CopilotRuntimeError(
                f"failed to start Copilot Runtime: {self._safe_error(exc)}"
            ) from exc

    async def stop(self) -> None:
        sessions = list(self.sessions.items())
        self.sessions.clear()
        for key, session in sessions:
            try:
                await session.disconnect()
                self.store.set_status(key, "disconnected")
            except (OSError, RuntimeError) as exc:
                log.warning("Failed to disconnect session: %s", self._safe_error(exc))
        if self.client is not None:
            await self.client.stop()
            self.client = None

    async def _create(self, key: str) -> Any:
        session_id = str(uuid.uuid4())
        try:
            session = await self._require_client().create_session(
                session_id=session_id,
                **self._session_kwargs_for(session_id),
            )
        except Exception as exc:
            raise CopilotRuntimeError(
                f"failed to create Copilot session: {self._safe_error(exc)}"
            ) from exc
        if session.session_id != session_id:
            with contextlib.suppress(OSError, RuntimeError):
                await session.disconnect()
            raise CopilotRuntimeError(
                "Copilot Runtime returned a different session ID than requested"
            )
        self.sessions[key] = session
        self.store.put(
            key,
            self.config.relay.channel,
            session.session_id,
            self.config.copilot.model.name,
            self.config_fingerprint,
        )
        return session

    async def _resume(self, key: str, session_id: str) -> Any:
        self.store.set_status(key, "resuming")
        try:
            session = await self._require_client().resume_session(
                session_id, **self._session_kwargs_for(session_id)
            )
        except Exception as exc:
            safe_error = self._safe_error(exc)
            self.store.set_status(key, "resume_error", safe_error)
            if self.config.copilot.resume_failure == "new":
                log.error("Resume failed; configured to create new session: %s", safe_error)
                self.store.delete(key)
                return await self._create(key)
            raise CopilotRuntimeError(
                f"failed to resume session {session_id}; context kept: {safe_error}"
            ) from exc
        self.sessions[key] = session
        self.store.set_status(key, "active")
        return session

    async def get_or_create(self, key: str) -> Any:
        if key in self.sessions:
            return self.sessions[key]
        mapping = self.store.get(key)
        if mapping and mapping.config_fingerprint != self.config_fingerprint:
            if self.config.copilot.configuration_change == "new":
                self.store.delete(key)
                return await self._create(key)
            raise CopilotRuntimeError(
                "session model/MCP/skills/agent configuration changed; "
                "use /new or set configuration_change: new"
            )
        return await self._resume(key, mapping.session_id) if mapping else await self._create(key)

    async def send(self, key: str, prompt: str) -> str:
        """同步发送 prompt 到 Copilot 会话并等待完成。

        使用活动刷新式超时(移植自旧 nlp_worker_acp.py):
        - 通过 session.on() 订阅 SDK 事件, 任意事件都刷新 _last_activity;
        - 以 copilot.max_idle_seconds(默认 300s)为窗口循环等待, 只要 copilot 还在
          持续输出/调 MCP(有活动)就不断续期, 只有真正"死寂"(超过阈值无任何事件)
          才 abort 报超时。
        解决长任务(如创建状态机)被固定 timeout 误判超时的问题。
        注: 首次 send 前 _last_activity 即已记录(冷启动也计入), 因此首轮窗口即含
        启动耗时, 不会把冷启动误判成死寂。
        """
        lock = self.locks.setdefault(key, asyncio.Lock())
        async with lock:
            session = await self.get_or_create(key)
            # 会话完成/报错 信号
            done = asyncio.Event()
            error: Exception | None = None
            last_assistant: Any = None

            def on_event(event: Any) -> None:
                # 任意事件都代表 copilot 仍在活动, 刷新活动时间戳
                self._last_activity = time.time()
                match getattr(event, "data", None):
                    case AssistantMessageData():  # noqa: F841
                        nonlocal last_assistant
                        last_assistant = event
                    case SessionIdleData():  # noqa: F841
                        done.set()
                    case SessionErrorData() as data:  # noqa: F841
                        nonlocal error
                        error = Exception(
                            data.message if data else "Copilot session error"
                        )
                        done.set()

            max_idle = float(self.config.copilot.max_idle_seconds)
            unsubscribe = session.on(on_event)
            try:
                await session.send(prompt)
            except Exception as exc:
                unsubscribe()
                raise CopilotRuntimeError(
                    f"Copilot request failed: {self._safe_error(exc)}"
                ) from exc

            # 活动刷新式超时循环: 有活动续期, 死寂才超时
            try:
                while True:
                    try:
                        await asyncio.wait_for(asyncio.shield(done.wait()), timeout=max_idle)
                        break
                    except TimeoutError:
                        # 这期间是否有活动? 有则继续等; 无则真死寂
                        if time.time() - self._last_activity >= max_idle:
                            raise TimeoutError(
                                f"Copilot timed out after {max_idle:.0f}s of inactivity"
                            )
            except TimeoutError as exc:
                await session.abort()
                raise CopilotRuntimeError(
                    "Copilot timed out; cancellation sent"
                ) from exc
            finally:
                unsubscribe()

            if error is not None:
                raise CopilotRuntimeError(f"Copilot request failed: {self._safe_error(error)}")
            content = getattr(getattr(last_assistant, "data", None), "content", None)
            if not isinstance(content, str) or not content.strip():
                raise CopilotRuntimeError("Copilot returned no assistant message")
            self.store.set_status(key, "active")
            return content.strip()

    async def new_session(self, key: str) -> str:
        if old := self.sessions.pop(key, None):
            await old.disconnect()
        self.store.delete(key)
        return (await self._create(key)).session_id

    async def cancel(self, key: str) -> bool:
        if session := self.sessions.get(key):
            await session.abort()
            return True
        return False

    def session_id(self, key: str) -> str:
        if session := self.sessions.get(key):
            return str(session.session_id)
        mapping = self.store.get(key)
        if mapping:
            return mapping.session_id
        raise CopilotRuntimeError("Copilot session is not available")

    def status(self, key: str) -> str:
        mapping = self.store.get(key)
        if mapping is None:
            return "No Copilot session yet. Send a message to create one."
        connected = "connected" if key in self.sessions else "persisted; resumes next turn"
        return (
            f"Session: {mapping.session_id}\nModel: {mapping.model_name}\n"
            f"State: {connected} ({mapping.status})\n"
            f"Config fingerprint: {mapping.config_fingerprint[:12]}"
        )
