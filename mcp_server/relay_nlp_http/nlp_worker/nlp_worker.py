#!/usr/bin/env python3
"""Drop-in NLP worker for the existing Feishu → relay → Kanzi chain."""

from __future__ import annotations

import argparse
import asyncio
import logging
import logging.handlers
import os
import re
import stat
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast
from urllib.parse import unquote, urlencode, urlparse

import httpx

from copilot_runtime import (
    AppConfig,
    BridgeError,
    CopilotRuntime,
    CopilotRuntimeError,
    application_directory,
    list_available_models,
    load_config,
    validate_runtime_config,
)
from relay_client import (
    RelayClient,
    RelayMessageError,
    RelayRequest,
    output_message,
    parse_relay_message,
    thinking_message,
    progress_message,
)
from session_store import SessionStore

log = logging.getLogger("nlp-worker")

CommandName = Literal["new", "status", "cancel", "help"]
HELP_TEXT = (
    "Commands:\n"
    "/new - create a new Copilot session\n"
    "/status - show current session\n"
    "/cancel - cancel the active turn\n"
    "/help - show this help"
)
_FILE_MARKER = re.compile(
    r"\[FILE[^\]]*\]\s*(?:\r?\n)?\s*path\s*=\s*"
    r"(?:[\"']([^\"']+)[\"']|([^\r\n;]+))",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class Command:
    name: CommandName


def parse_command(text: str) -> Command | None:
    name = text.strip().partition(" ")[0].removeprefix("/").lower()
    if not text.strip().startswith("/") or name not in {"new", "status", "cancel", "help"}:
        return None
    return Command(cast(CommandName, name))


def split_message(text: str, limit: int) -> list[str]:
    if not text:
        return [""]
    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        window = remaining[: limit + 1]
        split_at = max(
            window.rfind(mark, 0, limit + 1)
            for mark in ("\n", "。", "！", "？", " ")
        )
        split_at = limit if split_at < limit // 2 else split_at + 1
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    if remaining or not chunks:
        chunks.append(remaining)
    return chunks


def extract_file_marker(text: str) -> tuple[str, str | None]:
    match = _FILE_MARKER.search(text)
    if not match:
        return text, None
    path = (match.group(1) or match.group(2) or "").strip().rstrip("`")
    clean = (text[: match.start()] + text[match.end() :]).strip()
    return clean, path or None


class LegacyFileBridge:
    """Preserve [FILE_DOWNLOAD] and [FILE] behavior of nlp_worker_acp.py."""

    def __init__(
        self,
        config: AppConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self._transport = transport

    @staticmethod
    def _origin(url: str) -> tuple[str, str, int]:
        parsed = urlparse(url)
        try:
            port = parsed.port
        except ValueError as exc:
            raise BridgeError("file download URL has an invalid port") from exc
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise BridgeError("file download URL must use a valid http/https bridge origin")
        return (
            parsed.scheme,
            parsed.hostname.casefold(),
            port or (443 if parsed.scheme == "https" else 80),
        )

    @staticmethod
    def _download_filename(raw_name: str | None, url: str) -> str:
        source = raw_name or Path(unquote(urlparse(url).path)).name or "file"
        safe = re.sub(r"[^\w.\-]", "_", source, flags=re.UNICODE).strip(" .")[:120]
        if not safe or safe in {".", ".."}:
            return "file"
        reserved = {"CON", "PRN", "AUX", "NUL"}
        reserved.update(f"{prefix}{index}" for prefix in ("COM", "LPT") for index in range(1, 10))
        if Path(safe).stem.upper() in reserved:
            safe = f"_{safe}"
        return safe

    @staticmethod
    def _unique_download_path(workspace: Path, filename: str) -> Path:
        candidate = workspace / filename
        counter = 1
        while candidate.exists():
            candidate = workspace / (
                f"{Path(filename).stem}-{counter}{Path(filename).suffix}"
            )
            counter += 1
        return candidate

    def _validated_upload_path(
        self,
        path_value: str,
        session_id: str | None = None,
    ) -> Path:
        candidate = Path(path_value)
        try:
            path = candidate.resolve(strict=True)
            file_stat = path.stat()
        except OSError as exc:
            raise BridgeError(f"cannot read returned file: {candidate}") from exc
        if not stat.S_ISREG(file_stat.st_mode):
            raise BridgeError(f"returned upload path is not a regular file: {path}")

        compatibility = self.config.compatibility
        roots = [
            self.config.copilot.working_directory,
            *compatibility.upload_allowed_roots,
        ]
        resolved_roots = [root.resolve() for root in roots]
        if any(path == root or path.is_relative_to(root) for root in resolved_roots):
            return path

        base_directory = self.config.copilot.base_directory
        session_state = (base_directory / "session-state").resolve() if base_directory else None
        if session_state:
            try:
                relative = path.relative_to(session_state)
            except ValueError:
                pass
            else:
                parts = relative.parts
                if (
                    len(parts) >= 3
                    and parts[0]
                    and parts[1].casefold() == "files"
                    and (session_id is None or parts[0] == session_id)
                ):
                    return path

        allowed = [str(root) for root in resolved_roots]
        if session_state:
            allowed.append(str(session_state / "<session-id>" / "files"))
        raise BridgeError(
            f"refusing to upload file outside allowed roots: {path}; "
            f"allowed roots: {', '.join(allowed)}"
        )

    async def handle_download(
        self,
        instruction: str,
    ) -> str:
        values: dict[str, str] = {}
        for line in instruction.splitlines()[1:]:
            key, separator, value = line.partition("=")
            if separator:
                values[key.strip().lower()] = value.strip()
        url = values.get("url")
        if not url:
            raise BridgeError("file download request has no url")
        bridge_http = self.config.compatibility.bridge_http
        if not bridge_http:
            raise BridgeError(
                "[FILE_DOWNLOAD] received but compatibility.bridge_http is unset"
            )
        expected_origin = self._origin(bridge_http)
        requested_origin = self._origin(url)
        if requested_origin != expected_origin:
            raise BridgeError("file download URL origin does not match compatibility.bridge_http")

        workspace = self.config.copilot.working_directory.resolve()
        filename = self._download_filename(values.get("name"), url)
        destination = self._unique_download_path(workspace, filename)
        if destination.resolve().parent != workspace:
            raise BridgeError("file download destination escapes copilot.working_directory")
        temporary = workspace / f".download-{uuid.uuid4().hex}.part"
        total = 0
        try:
            timeout = httpx.Timeout(
                self.config.compatibility.download_timeout_seconds
            )
            async with (
                httpx.AsyncClient(
                    timeout=timeout,
                    follow_redirects=False,
                    transport=self._transport,
                ) as client,
                client.stream("GET", url) as response,
            ):
                if 300 <= response.status_code < 400:
                    raise BridgeError("file download redirects are not allowed")
                if response.status_code >= 400:
                    raise BridgeError(
                        f"file download failed with HTTP {response.status_code}"
                    )
                content_length = response.headers.get("content-length")
                if content_length:
                    try:
                        declared_size = int(content_length)
                    except ValueError as exc:
                        raise BridgeError("file download Content-Length is invalid") from exc
                    if declared_size > self.config.compatibility.max_upload_bytes:
                        raise BridgeError("download exceeds max_upload_bytes")
                with temporary.open("xb") as output:
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > self.config.compatibility.max_upload_bytes:
                            raise BridgeError("download exceeds max_upload_bytes")
                        output.write(chunk)
                    output.flush()
                    os.fsync(output.fileno())
            os.replace(temporary, destination)
        except httpx.TimeoutException as exc:
            raise BridgeError("file download timed out") from exc
        except httpx.RequestError as exc:
            raise BridgeError("file download request failed") from exc
        finally:
            temporary.unlink(missing_ok=True)
        return f"File saved to working directory:\n{destination}\nBytes: {total}"

    async def upload_marked_file(
        self,
        text: str,
        session_id: str | None = None,
    ) -> str:
        clean, path_value = extract_file_marker(text)
        if not path_value:
            return clean
        bridge_http = self.config.compatibility.bridge_http
        if not bridge_http:
            raise BridgeError("[FILE] returned but compatibility.bridge_http is unset")
        path = self._validated_upload_path(path_value, session_id)
        size = path.stat().st_size
        if size > self.config.compatibility.max_upload_bytes:
            raise BridgeError("upload exceeds max_upload_bytes")
        query = {"name": path.name}
        if self.config.compatibility.bridge_target_open_id:
            query["open_id"] = self.config.compatibility.bridge_target_open_id
        upload_url = f"{bridge_http.rstrip('/')}/upload?{urlencode(query)}"
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                upload_url,
                content=path.read_bytes(),
                headers={"Content-Type": "application/octet-stream"},
            )
            response.raise_for_status()
        return clean


class NLPWorker:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.store = SessionStore(
            config.storage.database_path,
            config.messages.dedup_ttl_seconds,
        )
        self.copilot = CopilotRuntime(config, self.store)
        self.files = LegacyFileBridge(config)
        self.queue: asyncio.Queue[RelayRequest] = asyncio.Queue(
            maxsize=config.messages.queue_size
        )
        self.relay = RelayClient(config.relay, self._on_relay_message)
        self.workers: list[asyncio.Task[None]] = []

    async def _on_relay_message(self, raw: str) -> None:
        try:
            request = parse_relay_message(raw)
        except RelayMessageError as exc:
            log.warning("Rejected relay message: %s", exc)
            await self._send_text(f"Error: {exc}")
            return
        if request is None or not self.store.claim_event(request.message_id):
            return
        try:
            self.queue.put_nowait(request)
        except asyncio.QueueFull:
            await self._send_text("Service busy: message queue is full.", request)

    async def _process_queue(self, index: int) -> None:
        while True:
            request = await self.queue.get()
            try:
                await self._handle_request(request)
            except asyncio.CancelledError:
                raise
            except (
                BridgeError,
                CopilotRuntimeError,
                RelayMessageError,
                httpx.HTTPError,
                OSError,
            ) as exc:
                log.error("Request failed worker=%s: %s", index, exc)
                await self._send_text(f"Error: {exc}", request)
            finally:
                self.queue.task_done()

    async def _handle_request(self, request: RelayRequest) -> None:
        key = request.conversation_key(self.config.relay)
        if len(request.text) > self.config.messages.max_input_chars:
            raise BridgeError(
                f"message has {len(request.text)} characters; "
                f"limit is {self.config.messages.max_input_chars}"
            )
        if command := parse_command(request.text):
            await self._handle_command(key, command, request)
            return
        if (
            self.config.compatibility.support_file_download_marker
            and request.text.startswith("[FILE_DOWNLOAD]")
        ):
            await self._send_text(
                await self.files.handle_download(request.text),
                request,
            )
            return
        await self.relay.send(thinking_message(self.config.compatibility.thinking_text))

        # 多阶段活动反馈: 把 copilot 的工具事件进度转发(progress_message)给 relay,
        # 节流由 CopilotRuntime.send 内部处理; progress 不触发桥的 _done_event。
        async def _on_progress(text: str) -> None:
            try:
                await self.relay.send(progress_message(text))
            except Exception:  # noqa: BLE001
                log.debug(f"progress 转发失败(忽略): {text[:60]}")

        response = await self.copilot.send(
            key,
            request.text,
            on_progress=_on_progress,
        )
        response = await self.files.upload_marked_file(
            response,
            self.copilot.session_id(key),
        )
        await self._send_text(response or "(no output)", request)

    async def _handle_command(
        self,
        key: str,
        command: Command,
        request: RelayRequest,
    ) -> None:
        if command.name == "help":
            text = HELP_TEXT
        elif command.name == "status":
            text = self.copilot.status(key)
        elif command.name == "new":
            text = f"Created new Copilot session: {await self.copilot.new_session(key)}"
        else:
            text = (
                "Cancellation sent."
                if await self.copilot.cancel(key)
                else "No connected Copilot session."
            )
        await self._send_text(text, request)

    async def _send_text(
        self,
        text: str,
        request: RelayRequest | None = None,
    ) -> None:
        chunks = split_message(text, self.config.messages.max_output_chars)
        for index, chunk in enumerate(chunks, start=1):
            rendered = f"({index}/{len(chunks)}) {chunk}" if len(chunks) > 1 else chunk
            await self.relay.send(
                output_message(
                    rendered,
                    self.config.compatibility.output_type,
                    request,
                )
            )

    async def run(self) -> None:
        self.store.open()
        await self.copilot.start()
        self.workers = [
            asyncio.create_task(self._process_queue(index))
            for index in range(self.config.messages.worker_count)
        ]
        log.info(
            "Worker ready: channel=%s model=%s",
            self.config.relay.channel,
            self.config.copilot.model.name,
        )
        try:
            await self.relay.run()
        finally:
            await self.stop()

    async def stop(self) -> None:
        await self.relay.stop()
        for worker in self.workers:
            worker.cancel()
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        await self.copilot.stop()
        self.store.close()


def configure_logging(config: AppConfig) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if config.logging.file:
        config.logging.file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            logging.handlers.RotatingFileHandler(
                config.logging.file,
                maxBytes=config.logging.max_bytes,
                backupCount=config.logging.backup_count,
                encoding="utf-8",
            )
        )
    logging.basicConfig(
        level=getattr(logging, config.logging.level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )


def default_config_path() -> Path:
    return application_directory() / "config.yaml"


async def async_main(config_path: str | Path) -> None:
    config = load_config(config_path)
    configure_logging(config)
    await NLPWorker(config).run()


def format_model_table(models: list[object]) -> str:
    headers = ("ID", "DISPLAY NAME", "REASONING EFFORTS", "DEFAULT REASONING")
    rows = [
        (
            str(getattr(model, "id", "-") or "-"),
            str(getattr(model, "name", "-") or "-"),
            ", ".join(getattr(model, "supported_reasoning_efforts", None) or []) or "-",
            str(getattr(model, "default_reasoning_effort", None) or "-"),
        )
        for model in sorted(models, key=lambda item: str(getattr(item, "id", "")).casefold())
    ]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]

    def render(row: tuple[str, ...]) -> str:
        return "  ".join(value.ljust(widths[index]) for index, value in enumerate(row)).rstrip()

    separator = tuple("-" * width for width in widths)
    return "\n".join([render(headers), render(separator), *(render(row) for row in rows)])


async def list_models_main(config_path: str | Path) -> None:
    config = load_config(config_path)
    models = await list_available_models(config)
    if not models:
        raise CopilotRuntimeError(
            "Copilot returned no models; check GitHub authorization and account access"
        )
    print(format_model_table(models))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GitHub Copilot SDK NLP worker for relay_multi.py"
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="YAML configuration path (default: config.yaml beside the executable)",
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="validate configuration and bundled runtime without connecting",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="list models available to the configured GitHub account, then exit",
    )
    args = parser.parse_args()
    config_path = args.config or default_config_path()
    try:
        if args.validate_config:
            config = load_config(config_path)
            runtime_path = validate_runtime_config(config)
            print(f"Configuration valid: {Path(config_path).resolve()}")
            if runtime_path:
                print(f"Bundled Copilot Runtime: {runtime_path}")
            return
        if args.list_models:
            asyncio.run(list_models_main(config_path))
            return
        asyncio.run(async_main(config_path))
    except KeyboardInterrupt:
        return
    except BridgeError as exc:
        print(f"Startup error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
