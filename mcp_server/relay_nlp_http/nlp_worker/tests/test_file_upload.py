import os
from pathlib import Path

import httpx
import pytest

from copilot_runtime import (
    AppConfig,
    CompatibilityConfig,
    CopilotConfig,
    ModelConfig,
    RelayConfig,
    RelayIdentityConfig,
)
from nlp_worker import BridgeError, LegacyFileBridge


def make_bridge(
    tmp_path: Path,
    *,
    extra_roots: list[Path] | None = None,
    max_bytes: int = 1024,
    handler=None,
) -> LegacyFileBridge:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    base = tmp_path / ".copilot-data"
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
            working_directory=workspace,
            base_directory=base,
            model=ModelConfig(name="test-model"),
        ),
        compatibility=CompatibilityConfig(
            bridge_http="http://localhost:8081/test",
            max_upload_bytes=max_bytes,
            upload_allowed_roots=extra_roots or [],
        ),
    )
    transport = httpx.MockTransport(handler) if handler else None
    return LegacyFileBridge(config, transport=transport)


def write_file(path: Path, content: bytes = b"image") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def downloaded_path(result: str) -> Path:
    return Path(result.splitlines()[1])


@pytest.mark.asyncio
async def test_legacy_download_stays_in_workspace_and_uses_unique_names(
    tmp_path: Path,
) -> None:
    body = b'{"source":"feishu"}'
    bridge = make_bridge(
        tmp_path,
        handler=lambda _request: httpx.Response(200, content=body),
    )
    instruction = (
        "[FILE_DOWNLOAD]\n"
        "url=http://localhost:8081/download/file\n"
        "name=../attachment.json"
    )

    first = downloaded_path(await bridge.handle_download(instruction))
    second = downloaded_path(await bridge.handle_download(instruction))

    workspace = (tmp_path / "workspace").resolve()
    assert first.parent == workspace
    assert second.parent == workspace
    assert first.name == "_attachment.json"
    assert second.name == "_attachment-1.json"
    assert first.read_bytes() == body
    assert second.read_bytes() == body
    assert not (tmp_path / ".copilot-data" / "session-state").exists()


class OversizedStream(httpx.AsyncByteStream):
    async def __aiter__(self):
        yield b"1234"
        yield b"5"


@pytest.mark.asyncio
async def test_legacy_download_size_failure_cleans_temporary_file(
    tmp_path: Path,
) -> None:
    bridge = make_bridge(
        tmp_path,
        max_bytes=4,
        handler=lambda _request: httpx.Response(200, stream=OversizedStream()),
    )

    with pytest.raises(BridgeError, match="download exceeds max_upload_bytes"):
        await bridge.handle_download(
            "[FILE_DOWNLOAD]\nurl=http://localhost:8081/download/file\nname=file.bin"
        )

    workspace = tmp_path / "workspace"
    assert not (workspace / "file.bin").exists()
    assert not list(workspace.glob("*.part"))


@pytest.mark.asyncio
async def test_legacy_download_enforces_bridge_origin_and_rejects_redirects(
    tmp_path: Path,
) -> None:
    bridge = make_bridge(
        tmp_path,
        handler=lambda _request: httpx.Response(
            302,
            headers={"Location": "http://localhost:8082/other"},
        ),
    )

    with pytest.raises(BridgeError, match="does not match"):
        await bridge.handle_download(
            "[FILE_DOWNLOAD]\nurl=http://localhost:8082/download/file"
        )
    with pytest.raises(BridgeError, match="redirects are not allowed"):
        await bridge.handle_download(
            "[FILE_DOWNLOAD]\nurl=http://localhost:8081/download/file"
        )


def test_workspace_file_is_allowed(tmp_path: Path) -> None:
    bridge = make_bridge(tmp_path)
    screenshot = write_file(tmp_path / "workspace" / "screenshot.png")

    assert bridge._validated_upload_path(str(screenshot)) == screenshot.resolve()


def test_runtime_session_files_attachment_is_allowed(tmp_path: Path) -> None:
    bridge = make_bridge(tmp_path)
    screenshot = write_file(
        tmp_path
        / ".copilot-data"
        / "session-state"
        / "session-123"
        / "files"
        / "kanzi-screenshot.svg"
    )

    assert bridge._validated_upload_path(str(screenshot)) == screenshot.resolve()


def test_runtime_attachment_is_restricted_to_current_session(tmp_path: Path) -> None:
    bridge = make_bridge(tmp_path)
    screenshot = write_file(
        tmp_path
        / ".copilot-data"
        / "session-state"
        / "session-b"
        / "files"
        / "kanzi-screenshot.svg"
    )

    with pytest.raises(BridgeError, match="outside allowed roots"):
        bridge._validated_upload_path(str(screenshot), "session-a")
    assert bridge._validated_upload_path(str(screenshot), "session-b") == screenshot.resolve()


@pytest.mark.parametrize(
    "relative",
    [
        Path(".copilot-data") / "auth.json",
        Path(".copilot-data") / "session-state" / "session-123" / "metadata.json",
        Path(".copilot-data") / "session-state" / "session-123" / "other" / "shot.png",
    ],
)
def test_base_directory_credentials_and_non_files_paths_are_rejected(
    tmp_path: Path, relative: Path
) -> None:
    bridge = make_bridge(tmp_path)
    sensitive = write_file(tmp_path / relative)

    with pytest.raises(BridgeError, match="outside allowed roots"):
        bridge._validated_upload_path(str(sensitive))


def test_explicit_allowed_root_is_allowed(tmp_path: Path) -> None:
    trusted = tmp_path / "trusted-exports"
    trusted.mkdir()
    bridge = make_bridge(tmp_path, extra_roots=[trusted])
    report = write_file(trusted / "report.svg")

    assert bridge._validated_upload_path(str(report)) == report.resolve()


def test_external_and_traversal_paths_are_rejected(tmp_path: Path) -> None:
    bridge = make_bridge(tmp_path)
    external = write_file(tmp_path / "outside" / "secret.txt")
    traversal = tmp_path / "workspace" / ".." / "outside" / "secret.txt"

    with pytest.raises(BridgeError, match="outside allowed roots"):
        bridge._validated_upload_path(str(external))
    with pytest.raises(BridgeError, match="outside allowed roots"):
        bridge._validated_upload_path(str(traversal))


def test_directory_is_rejected_as_non_regular_file(tmp_path: Path) -> None:
    bridge = make_bridge(tmp_path)

    with pytest.raises(BridgeError, match="not a regular file"):
        bridge._validated_upload_path(str(tmp_path / "workspace"))


@pytest.mark.asyncio
async def test_upload_size_limit_is_applied_before_http_request(tmp_path: Path) -> None:
    bridge = make_bridge(tmp_path, max_bytes=4)
    oversized = write_file(tmp_path / "workspace" / "large.svg", b"12345")

    with pytest.raises(BridgeError, match="upload exceeds max_upload_bytes"):
        await bridge.upload_marked_file(f"[FILE]\npath={oversized}")


def test_symlink_escaping_allowed_root_is_rejected_when_supported(tmp_path: Path) -> None:
    bridge = make_bridge(tmp_path)
    external = write_file(tmp_path / "outside" / "secret.txt")
    link = tmp_path / "workspace" / "linked.txt"
    try:
        os.symlink(external, link)
    except OSError:
        pytest.skip("file symlinks are unavailable on this Windows installation")

    with pytest.raises(BridgeError, match="outside allowed roots"):
        bridge._validated_upload_path(str(link))
