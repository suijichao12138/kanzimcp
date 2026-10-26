from pathlib import Path
from types import SimpleNamespace

import pytest

import copilot_runtime
from copilot_runtime import (
    AppConfig,
    CopilotConfig,
    CopilotRuntimeError,
    ModelConfig,
    RelayConfig,
    RelayIdentityConfig,
    StorageConfig,
    list_available_models,
)
from nlp_worker import format_model_table


def make_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
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
            base_directory=tmp_path / ".copilot-data",
            model=ModelConfig(name="unused-for-listing"),
        ),
        storage=StorageConfig(database_path=tmp_path / "bridge.db"),
        config_dir=tmp_path,
    )


@pytest.mark.asyncio
async def test_list_models_uses_config_and_stops_without_session(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[object] = []
    expected = [
        SimpleNamespace(
            id="gpt-5.6-sol",
            name="GPT-5.6 Sol",
            supported_reasoning_efforts=["low", "high"],
            default_reasoning_effort="high",
        )
    ]

    class FakeClient:
        def __init__(self, **options) -> None:
            calls.append(options)

        async def start(self) -> None:
            calls.append("start")

        async def list_models(self):
            calls.append("list_models")
            return expected

        async def stop(self) -> None:
            calls.append("stop")

        async def create_session(self, **_kwargs):
            raise AssertionError("model listing must not create a session")

    monkeypatch.setattr(copilot_runtime, "CopilotClient", FakeClient)
    monkeypatch.setattr(copilot_runtime, "validate_runtime_config", lambda _config: None)

    result = await list_available_models(make_config(tmp_path))

    assert result == expected
    assert calls[1:] == ["start", "list_models", "stop"]
    options = calls[0]
    assert options["working_directory"] == str(tmp_path)  # type: ignore[index]
    assert options["base_directory"] == str(tmp_path / ".copilot-data")  # type: ignore[index]
    assert options["use_logged_in_user"] is True  # type: ignore[index]


def test_model_table_uses_ids_and_missing_reasoning_markers() -> None:
    models = [
        SimpleNamespace(
            id="z-model",
            name="Zulu",
            supported_reasoning_efforts=None,
            default_reasoning_effort=None,
        ),
        SimpleNamespace(
            id="a-model",
            name="Alpha",
            supported_reasoning_efforts=["low", "medium"],
            default_reasoning_effort="medium",
        ),
    ]

    table = format_model_table(models)

    assert table.index("a-model") < table.index("z-model")
    assert "low, medium" in table
    assert "z-model  Zulu" in table
    assert "-" in table


@pytest.mark.asyncio
async def test_list_models_reports_auth_or_network_hint_and_stops(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[str] = []

    class FailingClient:
        def __init__(self, **_options) -> None:
            return None

        async def start(self) -> None:
            calls.append("start")

        async def list_models(self):
            raise RuntimeError("not authenticated")

        async def stop(self) -> None:
            calls.append("stop")

    monkeypatch.setattr(copilot_runtime, "CopilotClient", FailingClient)
    monkeypatch.setattr(copilot_runtime, "validate_runtime_config", lambda _config: None)

    with pytest.raises(
        CopilotRuntimeError,
        match="check GitHub authorization and network",
    ):
        await list_available_models(make_config(tmp_path))

    assert calls == ["start", "stop"]
