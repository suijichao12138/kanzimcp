import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import build_runtime_cache
import copilot_runtime
import nlp_worker
from copilot_runtime import (
    AppConfig,
    ConfigError,
    CopilotConfig,
    CopilotRuntime,
    ModelConfig,
    RelayConfig,
    RelayIdentityConfig,
    StorageConfig,
)
from session_store import SessionStore


def make_fake_runtime_bundle(directory: Path) -> tuple[Path, dict[str, str]]:
    directory.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    for name in ("copilot.exe", "copilot-runtime.exe", "runtime.node"):
        content = f"fake-{name}".encode()
        (directory / name).write_bytes(content)
        hashes[name] = hashlib.sha256(content).hexdigest()
    (directory / ".hostless-runtime-assets-v2").write_text("1\n", encoding="ascii")
    return directory / "copilot.exe", hashes


def test_source_defaults_to_config_beside_entry_point() -> None:
    assert nlp_worker.default_config_path() == Path(nlp_worker.__file__).resolve().parent / (
        "config.yaml"
    )


def test_login_script_uses_bundled_runtime_and_portable_home() -> None:
    script = (Path(__file__).resolve().parents[1] / "login_copilot.cmd").read_text(
        encoding="utf-8"
    )
    normalized = script.replace("\r\n", "\n")

    assert 'cd /d "%~dp0"' in normalized
    assert 'set "COPILOT_HOME=%~dp0.copilot-data"' in normalized
    assert 'set "COPILOT_RUNTIME=%~dp0_internal\\runtime\\copilot.exe"' in normalized
    assert '"%COPILOT_RUNTIME%" login' in normalized
    assert 'set "LOGIN_EXIT_CODE=%ERRORLEVEL%"' in normalized
    assert "exit /b %LOGIN_EXIT_CODE%" in normalized
    assert "type " not in normalized.casefold()
    assert "copy " not in normalized.casefold()


def test_build_script_locks_sdk_and_complete_runtime_bundle() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "build_portable.cmd").read_text(encoding="utf-8")
    spec = (root / "nlp_worker.spec").read_text(encoding="utf-8")

    assert "EXPECTED_SDK_VERSION=1.0.26" in script
    assert "EXPECTED_RUNTIME_VERSION=1.0.103" in script
    assert "build_runtime_cache.py" in script
    assert "Selecting the project-local Copilot Runtime cache" in script
    assert "download-runtime','--force'" not in script
    assert "Remove-Item -LiteralPath $env:COPILOT_CLI_EXTRACT_DIR" not in script
    assert "copilot-runtime.exe" in script
    assert "runtime.node" in script
    assert "runtime_bundle.rglob" in spec


def test_valid_canonical_cache_skips_download(
    tmp_path: Path, monkeypatch
) -> None:
    bundle = tmp_path / "build" / "copilot-runtime"
    runtime, _hashes = make_fake_runtime_bundle(bundle)
    calls: list[Path] = []
    output: list[str] = []
    monkeypatch.setattr(CopilotRuntime, "validate_sdk_version", lambda: None)
    monkeypatch.setattr(
        copilot_runtime, "read_runtime_version", lambda executable: "1.0.103"
    )

    selection = build_runtime_cache.ensure_runtime_cache(
        tmp_path,
        env_file=tmp_path / "build" / "runtime-env.cmd",
        release_marker=tmp_path / "build" / "runtime-version.txt",
        download_runner=lambda path: calls.append(path),
        output=output.append,
    )

    assert selection.executable == runtime.resolve()
    assert calls == []
    assert any("network download skipped" in line for line in output)


def test_incomplete_cache_reports_missing_files_and_downloads(
    tmp_path: Path, monkeypatch
) -> None:
    canonical = tmp_path / "build" / "copilot-runtime"
    canonical.mkdir(parents=True)
    (canonical / "copilot.exe").write_bytes(b"incomplete")
    calls: list[Path] = []
    output: list[str] = []
    monkeypatch.setattr(CopilotRuntime, "validate_sdk_version", lambda: None)
    monkeypatch.setattr(
        copilot_runtime, "read_runtime_version", lambda executable: "1.0.103"
    )

    def download(extract_dir: Path) -> None:
        calls.append(extract_dir)
        make_fake_runtime_bundle(extract_dir / "prebuilds" / "win32-x64")

    selection = build_runtime_cache.ensure_runtime_cache(
        tmp_path,
        env_file=tmp_path / "build" / "runtime-env.cmd",
        release_marker=tmp_path / "build" / "runtime-version.txt",
        download_runner=download,
        output=output.append,
    )

    assert calls == [tmp_path / "build" / "copilot-runtime-download"]
    assert selection.bundle == canonical.resolve()
    assert (canonical / "copilot-runtime.exe").is_file()
    assert (canonical / "runtime.node").is_file()
    assert any(
        "missing copilot-runtime.exe, runtime.node" in line for line in output
    )


def test_wrong_runtime_version_is_not_reused(
    tmp_path: Path, monkeypatch
) -> None:
    canonical = tmp_path / "build" / "copilot-runtime"
    make_fake_runtime_bundle(canonical)
    calls: list[Path] = []
    output: list[str] = []
    monkeypatch.setattr(CopilotRuntime, "validate_sdk_version", lambda: None)

    def read_version(executable: Path) -> str:
        return "1.0.103" if calls else "1.0.95-3"

    monkeypatch.setattr(copilot_runtime, "read_runtime_version", read_version)

    def download(extract_dir: Path) -> None:
        calls.append(extract_dir)
        make_fake_runtime_bundle(extract_dir / "prebuilds" / "win32-x64")

    selection = build_runtime_cache.ensure_runtime_cache(
        tmp_path,
        env_file=tmp_path / "build" / "runtime-env.cmd",
        release_marker=tmp_path / "build" / "runtime-version.txt",
        download_runner=download,
        output=output.append,
    )

    assert calls
    assert selection.bundle == canonical.resolve()
    assert any("expected 1.0.103, found 1.0.95-3" in line for line in output)


def test_frozen_paths_use_executable_and_bundle_directories(
    tmp_path: Path, monkeypatch
) -> None:
    executable = tmp_path / "portable" / "nlp_worker.exe"
    bundle = tmp_path / "portable" / "_internal"
    runtime = bundle / "runtime" / "copilot.exe"
    runtime.parent.mkdir(parents=True)
    runtime.write_bytes(b"runtime")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)

    assert copilot_runtime.application_directory() == executable.parent
    assert copilot_runtime.bundle_directory() == bundle
    assert copilot_runtime.bundled_runtime_path() == runtime
    assert nlp_worker.default_config_path() == executable.parent / "config.yaml"


def test_frozen_missing_runtime_has_clear_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    with pytest.raises(ConfigError, match="re-extract the complete portable folder"):
        copilot_runtime.bundled_runtime_path()


@pytest.mark.asyncio
async def test_frozen_runtime_is_explicit_sdk_connection(
    tmp_path: Path, monkeypatch
) -> None:
    bundle = tmp_path / "_internal"
    runtime_path = bundle / "runtime" / "copilot.exe"
    runtime_path.parent.mkdir(parents=True)
    runtime_path.write_bytes(b"runtime")
    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

        async def start(self) -> None:
            return None

    config = AppConfig(
        relay=RelayConfig(
            url="ws://localhost:58080/test",
            channel="test",
            allowed_channels={"test"},
            identity=RelayIdentityConfig(
                mode="dedicated_channel",
                dedicated_principal_id="test",
            ),
        ),
        copilot=CopilotConfig(
            working_directory=tmp_path,
            model=ModelConfig(name="test-model"),
        ),
        storage=StorageConfig(database_path=tmp_path / "bridge.db"),
    )
    store = SessionStore(config.storage.database_path)
    worker = CopilotRuntime(config, store)

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)
    monkeypatch.setattr(copilot_runtime, "CopilotClient", FakeClient)
    monkeypatch.setattr(
        copilot_runtime, "validate_runtime_config", lambda config: runtime_path
    )

    await worker.start()

    connection = captured["connection"]
    assert connection.path == str(runtime_path)  # type: ignore[union-attr]


def test_runtime_version_parser_accepts_official_output() -> None:
    assert (
        copilot_runtime.parse_runtime_version("GitHub Copilot CLI 1.0.103\n")
        == "1.0.103"
    )


def test_non_windows_runtime_version_uses_version_command(
    tmp_path: Path, monkeypatch
) -> None:
    runtime = tmp_path / "copilot"
    runtime.write_bytes(b"runtime")
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(
        copilot_runtime.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="GitHub Copilot CLI 1.0.103\n",
            stderr="",
        ),
    )

    assert copilot_runtime.read_runtime_version(runtime) == "1.0.103"


def test_sdk_and_runtime_pins_must_match(monkeypatch) -> None:
    monkeypatch.setattr(
        copilot_runtime,
        "version",
        lambda package: copilot_runtime.EXPECTED_SDK_VERSION,
    )
    monkeypatch.setattr(
        copilot_runtime,
        "SDK_RUNTIME_VERSION",
        copilot_runtime.EXPECTED_RUNTIME_VERSION,
    )

    CopilotRuntime.validate_sdk_version()


def test_wrong_sdk_version_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(copilot_runtime, "version", lambda package: "1.0.11")

    with pytest.raises(ConfigError, match="expected 1.0.26, installed 1.0.11"):
        CopilotRuntime.validate_sdk_version()


def test_runtime_executable_and_marker_must_match(
    tmp_path: Path, monkeypatch
) -> None:
    runtime, _hashes = make_fake_runtime_bundle(tmp_path)
    marker = tmp_path / "COPILOT_RUNTIME_VERSION.txt"
    marker.write_text("GitHub Copilot CLI 1.0.82\n", encoding="utf-8")
    monkeypatch.setattr(
        copilot_runtime, "read_runtime_version", lambda executable: "1.0.103"
    )

    with pytest.raises(ConfigError, match="marker mismatch"):
        copilot_runtime.validate_runtime_binary(runtime, marker_path=marker)


def test_runtime_executable_and_marker_matching_version_pass(
    tmp_path: Path, monkeypatch
) -> None:
    runtime, hashes = make_fake_runtime_bundle(tmp_path)
    marker = tmp_path / "COPILOT_RUNTIME_VERSION.txt"
    marker.write_text(
        "GitHub Copilot CLI 1.0.103\n"
        + "".join(
            f"{name} SHA256 {digest}\n" for name, digest in hashes.items()
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        copilot_runtime, "read_runtime_version", lambda executable: "1.0.103"
    )

    assert (
        copilot_runtime.validate_runtime_binary(runtime, marker_path=marker)
        == "1.0.103"
    )


def test_runtime_marker_rejects_replaced_bundle_file(
    tmp_path: Path, monkeypatch
) -> None:
    runtime, hashes = make_fake_runtime_bundle(tmp_path)
    marker = tmp_path / "COPILOT_RUNTIME_VERSION.txt"
    marker.write_text(
        "GitHub Copilot CLI 1.0.103\n"
        + "".join(
            f"{name} SHA256 {digest}\n" for name, digest in hashes.items()
        ),
        encoding="utf-8",
    )
    (tmp_path / "runtime.node").write_bytes(b"replaced")
    monkeypatch.setattr(
        copilot_runtime, "read_runtime_version", lambda executable: "1.0.103"
    )

    with pytest.raises(ConfigError, match="bundle hash mismatch"):
        copilot_runtime.validate_runtime_binary(runtime, marker_path=marker)


def test_runtime_executable_wrong_version_is_rejected(
    tmp_path: Path, monkeypatch
) -> None:
    runtime, _hashes = make_fake_runtime_bundle(tmp_path)
    monkeypatch.setattr(
        copilot_runtime, "read_runtime_version", lambda executable: "1.0.95-3"
    )

    with pytest.raises(ConfigError, match="expected 1.0.103, found 1.0.95-3"):
        copilot_runtime.validate_runtime_binary(runtime)
