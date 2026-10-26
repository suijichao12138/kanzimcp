from pathlib import Path

from copilot_runtime import MCPRemoteConfig, MCPStdioConfig, convert_mcp_servers


def test_convert_stdio_and_http_mcp() -> None:
    converted = convert_mcp_servers(
        {
            "local": MCPStdioConfig(
                type="stdio",
                command="python",
                args=["server.py"],
                env={"A": "B"},
                cwd=Path("C:/work"),
                timeout_seconds=12,
            ),
            "kanzi": MCPRemoteConfig(
                type="http",
                url="http://localhost:9001/kanzistudio_mcp",
                headers={"X-Kanzi-User": "test"},
                tools=["*"],
                timeout_seconds=300,
            ),
        }
    )

    assert converted["local"]["working_directory"] == "C:\\work"
    assert converted["local"]["timeout"] == 12_000
    assert converted["kanzi"]["headers"] == {"X-Kanzi-User": "test"}
    assert converted["kanzi"]["timeout"] == 300_000


def test_disabled_mcp_is_omitted() -> None:
    converted = convert_mcp_servers(
        {
            "off": MCPRemoteConfig(
                enabled=False,
                type="sse",
                url="https://example.test/sse",
            )
        }
    )
    assert converted == {}
