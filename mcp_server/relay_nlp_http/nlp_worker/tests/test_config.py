import re
from pathlib import Path

import pytest

from copilot_runtime import ConfigError, load_config


def write_config(path: Path, provider: str = "github") -> None:
    provider_block = (
        "type: github"
        if provider == "github"
        else """
        type: openai
        base_url: https://oneapi.example.com/v1
        api_key: ${BYOK_KEY}
        wire_api: responses
        """
    )
    path.write_text(
        f"""
relay:
  url: ws://localhost:58080/test
  channel: test
  allowed_channels: [test]
  identity:
    mode: dedicated_channel
    dedicated_principal_id: test-user
copilot:
  github_token: ${{GH_TOKEN}}
  use_logged_in_user: false
  working_directory: .
  model:
    name: test-model
    provider:
      {provider_block}
storage:
  database_path: ./data/test.db
""",
        encoding="utf-8",
    )


def test_load_config_expands_environment_and_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GH_TOKEN", "secret-token")
    monkeypatch.setenv("BYOK_KEY", "byok-secret")
    path = tmp_path / "config.yaml"
    write_config(path, "openai")

    config = load_config(path)

    assert config.copilot.github_token == "secret-token"
    assert config.copilot.model.provider.to_sdk() == {
        "type": "openai",
        "base_url": "https://oneapi.example.com/v1",
        "api_key": "byok-secret",
        "wire_api": "responses",
    }
    assert config.storage.database_path == (tmp_path / "data/test.db").resolve()


def test_missing_environment_variable_is_clear(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("GH_TOKEN", raising=False)
    path = tmp_path / "config.yaml"
    write_config(path)

    with pytest.raises(ConfigError, match="GH_TOKEN"):
        load_config(path)


def test_relay_channel_must_match_url(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GH_TOKEN", "x")
    path = tmp_path / "config.yaml"
    write_config(path)
    text = path.read_text(encoding="utf-8").replace("channel: test", "channel: other")
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ConfigError, match="does not match"):
        load_config(path)


def test_missing_working_directory_reports_field_and_full_path(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("GH_TOKEN", "x")
    path = tmp_path / "config.yaml"
    write_config(path)
    missing = tmp_path / "missing-project"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "working_directory: .",
            "working_directory: ./missing-project",
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigError,
        match=re.escape(f"copilot.working_directory does not exist: {missing}"),
    ):
        load_config(path)


def test_working_directory_must_be_directory(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GH_TOKEN", "x")
    path = tmp_path / "config.yaml"
    write_config(path)
    file_path = tmp_path / "project.txt"
    file_path.write_text("not a directory", encoding="utf-8")
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "working_directory: .",
            "working_directory: ./project.txt",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match=r"copilot\.working_directory is not a directory"):
        load_config(path)


def test_enabled_stdio_mcp_cwd_must_exist(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GH_TOKEN", "x")
    path = tmp_path / "config.yaml"
    write_config(path)
    path.write_text(
        path.read_text(encoding="utf-8")
        + """
mcp_servers:
  local-tools:
    enabled: true
    type: stdio
    command: server.exe
    cwd: ./missing-mcp
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigError,
        match=r"mcp_servers\.local-tools\.cwd does not exist:",
    ):
        load_config(path)


def test_disabled_stdio_mcp_cwd_is_not_required(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GH_TOKEN", "x")
    path = tmp_path / "config.yaml"
    write_config(path)
    path.write_text(
        path.read_text(encoding="utf-8")
        + """
mcp_servers:
  local-tools:
    enabled: false
    type: stdio
    command: server.exe
    cwd: ./missing-mcp
""",
        encoding="utf-8",
    )

    assert load_config(path).mcp_servers["local-tools"].enabled is False


def test_upload_allowed_roots_resolve_from_config_directory(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("GH_TOKEN", "x")
    path = tmp_path / "config.yaml"
    trusted = tmp_path / "trusted-exports"
    trusted.mkdir()
    write_config(path)
    path.write_text(
        path.read_text(encoding="utf-8")
        + """
compatibility:
  upload_allowed_roots:
    - ./trusted-exports
""",
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.compatibility.upload_allowed_roots == [trusted.resolve()]


def test_large_output_path_is_resolved_and_session_templated(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("GH_TOKEN", "x")
    path = tmp_path / "config.yaml"
    write_config(path)
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "working_directory: .",
            """working_directory: .
  base_directory: ./.copilot-data
  large_output:
    enabled: true
    max_size_bytes: 4096
    output_directory: ./.copilot-data/session-state/{session_id}/files""",
        ),
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.copilot.large_output.output_directory == (
        tmp_path / ".copilot-data" / "session-state" / "{session_id}" / "files"
    ).resolve()


def test_artifact_origin_requires_explicit_port(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GH_TOKEN", "x")
    path = tmp_path / "config.yaml"
    write_config(path)
    path.write_text(
        path.read_text(encoding="utf-8")
        + """
artifacts:
  enabled: true
  allowed_origins:
    - https://downloads.example.com
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="explicit http\\(s\\)://host:port"):
        load_config(path)
