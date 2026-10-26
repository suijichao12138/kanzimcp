import base64
import json
from pathlib import Path

import httpx
import pytest
from copilot import ToolInvocation

from copilot_runtime import (
    AppConfig,
    ArtifactConfig,
    ArtifactError,
    ArtifactManager,
    CopilotConfig,
    ModelConfig,
    RelayConfig,
    RelayIdentityConfig,
)


def make_manager(
    tmp_path: Path,
    handler=None,
    *,
    max_bytes: int = 1024 * 1024,
    output_chars: int = 512,
) -> ArtifactManager:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
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
            base_directory=tmp_path / ".copilot-data",
            model=ModelConfig(name="test-model"),
        ),
        artifacts=ArtifactConfig(
            enabled=True,
            allowed_origins=["http://mcp.test:9001"],
            max_download_bytes=max_bytes,
            max_tool_output_chars=output_chars,
        ),
    )
    transport = httpx.MockTransport(handler) if handler else None
    return ArtifactManager(config, transport=transport)


@pytest.mark.asyncio
async def test_download_is_session_isolated_and_body_is_not_returned(
    tmp_path: Path,
) -> None:
    secret_body = b'{"secret":"BODY_MUST_NOT_REACH_CONTEXT","items":[1,2]}'

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            content=secret_body,
        )

    manager = make_manager(tmp_path, handler)
    tool = manager.build_tools()[0]
    result = await tool.handler(  # type: ignore[union-attr]
        ToolInvocation(
            session_id="session-a",
            arguments={"url": "http://mcp.test:9001/result"},
        )
    )

    assert "BODY_MUST_NOT_REACH_CONTEXT" not in result.text_result_for_llm
    path_line = next(
        line for line in result.text_result_for_llm.splitlines() if line.startswith("path=")
    )
    path = Path(path_line.removeprefix("path="))
    assert path.read_bytes() == secret_body
    assert path.parent == (
        tmp_path / ".copilot-data" / "session-state" / "session-a" / "files"
    ).resolve()
    assert not list(path.parent.glob("*.part"))


@pytest.mark.asyncio
async def test_download_rejects_origin_redirect_size_and_mime(tmp_path: Path) -> None:
    manager = make_manager(
        tmp_path,
        lambda _request: httpx.Response(
            302,
            headers={"Location": "http://evil.test:9001/file"},
        ),
        max_bytes=1024,
    )
    with pytest.raises(ArtifactError, match="origin is not allowed"):
        await manager.download_url("session-a", "http://mcp.test:9002/file")
    with pytest.raises(ArtifactError, match="redirects are not allowed"):
        await manager.download_url("session-a", "http://mcp.test:9001/file")

    oversized = make_manager(
        tmp_path,
        lambda _request: httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            content=b'{"value":"' + (b"x" * 2048) + b'"}',
        ),
        max_bytes=1024,
    )
    with pytest.raises(ArtifactError, match="max_download_bytes"):
        await oversized.download_url("session-b", "http://mcp.test:9001/file")
    files = tmp_path / ".copilot-data" / "session-state" / "session-b" / "files"
    assert not list(files.glob("*.part"))

    mismatch = make_manager(
        tmp_path,
        lambda _request: httpx.Response(
            200,
            headers={"Content-Type": "image/png"},
            content=b'{"valid":"json"}',
        ),
    )
    with pytest.raises(ArtifactError, match="MIME mismatch"):
        await mismatch.download_url("session-c", "http://mcp.test:9001/file")


def test_bounded_read_search_and_huge_single_line_json(tmp_path: Path) -> None:
    manager = make_manager(tmp_path, output_chars=256)
    root = tmp_path / ".copilot-data" / "session-state" / "session-a" / "files"
    root.mkdir(parents=True)
    text = root / "large.txt"
    text.write_text(("prefix keyword suffix " * 10_000), encoding="utf-8")
    huge_json = root / "large.json"
    huge_json.write_text(
        json.dumps({"payload": "x" * 500_000}, separators=(",", ":")),
        encoding="utf-8",
    )

    read_result = manager.read_text("session-a", str(text), max_chars=200)
    search_result = manager.search_text("session-a", str(text), "keyword")
    json_result = manager.query_json(
        "session-a",
        str(huge_json),
        "$.payload",
        max_chars=220,
    )

    assert len(read_result) <= 200
    assert len(search_result) <= 256
    assert len(json_result) <= 220
    assert "truncated" in json_result


@pytest.mark.asyncio
async def test_base64_png_materialization_and_session_isolation(tmp_path: Path) -> None:
    manager = make_manager(tmp_path)
    png = b"\x89PNG\r\n\x1a\n" + b"safe-image"
    root = tmp_path / ".copilot-data" / "session-state" / "session-a" / "files"
    root.mkdir(parents=True)
    source = root / "result.json"
    source.write_text(
        json.dumps(
            {
                "image": (
                    "data:image/png;base64,"
                    + base64.b64encode(png).decode("ascii")
                )
            }
        ),
        encoding="utf-8",
    )

    path, mime, size = await manager.materialize_image(
        "session-a",
        source_path=str(source),
        json_path="$.image",
        filename="kanzi-screenshot",
    )

    assert mime == "image/png"
    assert size == len(png)
    assert path.read_bytes() == png
    assert path.name == "kanzi-screenshot.png"
    with pytest.raises(ArtifactError, match="outside the current session"):
        manager.read_text("session-b", str(path))
