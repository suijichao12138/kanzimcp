import asyncio
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
from copilot.generated.session_events import (
    AssistantMessageData,
    SessionErrorData,
    SessionIdleData,
    ToolExecutionCompleteData,
    ToolExecutionCompleteError,
    ToolExecutionStartData,
)

from copilot_runtime import (
    AgentConfig,
    AppConfig,
    CopilotConfig,
    CopilotRuntime,
    CopilotRuntimeError,
    LargeOutputConfig,
    MessageConfig,
    ModelConfig,
    RelayConfig,
    RelayIdentityConfig,
    StorageConfig,
)
from relay_client import RelayRequest
from session_store import SessionStore


@dataclass
class FakeSession:
    session_id: str
    calls: list[str]
    aborted: bool = False
    disconnected: bool = False
    callback: object | None = None

    def on(self, callback):
        self.callback = callback

        def unsubscribe() -> None:
            self.callback = None

        return unsubscribe

    async def send(self, prompt: str) -> None:
        await asyncio.sleep(0.01)
        self.calls.append(prompt)
        assert callable(self.callback)
        self.callback(
            SimpleNamespace(
                data=AssistantMessageData(
                    content=f"{self.session_id}:{prompt}",
                    message_id=f"message-{self.session_id}",
                )
            )
        )
        self.callback(SimpleNamespace(data=SessionIdleData()))

    async def abort(self) -> None:
        self.aborted = True

    async def disconnect(self) -> None:
        self.disconnected = True


class FakeClient:
    def __init__(self, start: int = 0) -> None:
        self.start = start
        self.created: list[FakeSession] = []
        self.resumed: list[str] = []
        self.created_kwargs: list[dict[str, object]] = []
        self.resumed_kwargs: list[dict[str, object]] = []

    async def create_session(self, **kwargs) -> FakeSession:
        self.created_kwargs.append(kwargs)
        session = FakeSession(str(kwargs["session_id"]), [])
        self.created.append(session)
        return session

    async def resume_session(self, session_id: str, **kwargs) -> FakeSession:
        self.resumed.append(session_id)
        self.resumed_kwargs.append(kwargs)
        return FakeSession(session_id, [])


@dataclass
class ToolFailureSession(FakeSession):
    async def send(self, prompt: str) -> None:
        self.calls.append(prompt)
        assert callable(self.callback)
        self.callback(
            SimpleNamespace(
                data=ToolExecutionStartData(
                    tool_call_id="call-internal-id",
                    tool_name="mcp",
                    mcp_server_name="kanzi-studio-mcp",
                    mcp_tool_name="kz_invoke",
                    turn_id="turn-1",
                )
            )
        )
        self.callback(
            SimpleNamespace(
                data=ToolExecutionCompleteData(
                    success=False,
                    tool_call_id="call-internal-id",
                    error=ToolExecutionCompleteError(
                        code="MCP_ERROR",
                        message="Kanzi endpoint unavailable",
                    ),
                    turn_id="turn-1",
                )
            )
        )
        self.callback(SimpleNamespace(data=SessionIdleData()))


@dataclass
class SessionFailureSession(FakeSession):
    async def send(self, prompt: str) -> None:
        self.calls.append(prompt)
        assert callable(self.callback)
        self.callback(
            SimpleNamespace(
                data=SessionErrorData(
                    error_type="runtime",
                    message="session crashed",
                )
            )
        )


def make_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        relay=RelayConfig(
            url="ws://localhost:58080/test",
            channel="test",
            allowed_channels={"test"},
            identity=RelayIdentityConfig(mode="message_fields"),
        ),
        copilot=CopilotConfig(
            working_directory=tmp_path,
            base_directory=tmp_path / ".copilot-data",
            large_output=LargeOutputConfig(
                enabled=True,
                output_directory=(
                    tmp_path
                    / ".copilot-data"
                    / "session-state"
                    / "{session_id}"
                    / "files"
                ),
            ),
            model=ModelConfig(name="model-x"),
            agent=AgentConfig(system_prompt="prompt"),
        ),
        messages=MessageConfig(worker_count=2),
        storage=StorageConfig(database_path=tmp_path / "bridge.db"),
    )


@pytest.mark.asyncio
async def test_tool_attempt_failure_is_not_reported_as_turn_failure(
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    store = SessionStore(config.storage.database_path)
    store.open()
    runtime = CopilotRuntime(config, store)
    key = "channel=test|user_id=alice"
    runtime.sessions[key] = ToolFailureSession("session-1", [])
    progress: list[str] = []

    result = await runtime.send(key, "do work", on_progress=progress.append)

    expected = (
        "↪️ 工具 kanzi-studio-mcp/kz_invoke 本次调用未成功："
        "Kanzi endpoint unavailable；Copilot 将继续处理"
    )
    assert result == expected
    assert progress[-1] == expected
    assert "call-internal-id" not in progress[-1]
    assert "任务失败" not in progress[-1]
    store.close()


@pytest.mark.asyncio
async def test_session_error_remains_a_turn_failure(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    store = SessionStore(config.storage.database_path)
    store.open()
    runtime = CopilotRuntime(config, store)
    key = "channel=test|user_id=alice"
    runtime.sessions[key] = SessionFailureSession("session-1", [])

    with pytest.raises(
        CopilotRuntimeError,
        match="Copilot request failed: session crashed",
    ):
        await runtime.send(key, "do work")
    store.close()


@pytest.mark.asyncio
async def test_two_users_are_isolated_and_resume_after_restart(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    store = SessionStore(config.storage.database_path)
    store.open()
    first = CopilotRuntime(config, store)
    first_client = FakeClient()
    first.client = first_client  # type: ignore[assignment]
    alice = "channel=test|chat_id=group|user_id=alice|scope=chat"
    bob = "channel=test|chat_id=group|user_id=bob|scope=chat"

    replies = await asyncio.gather(
        first.send(alice, "A"),
        first.send(bob, "B"),
    )

    alice_id = store.get(alice).session_id  # type: ignore[union-attr]
    bob_id = store.get(bob).session_id  # type: ignore[union-attr]
    assert replies == [f"{alice_id}:A", f"{bob_id}:B"]
    assert alice_id != bob_id
    created_directories = {
        str(kwargs["large_output"]["output_directory"])  # type: ignore[index]
        for kwargs in first_client.created_kwargs
    }
    assert created_directories == {
        str(tmp_path / ".copilot-data" / "session-state" / alice_id / "files"),
        str(tmp_path / ".copilot-data" / "session-state" / bob_id / "files"),
    }

    restarted = CopilotRuntime(config, store)
    restarted_client = FakeClient(start=10)
    restarted.client = restarted_client  # type: ignore[assignment]
    restored = await restarted.send(alice, "A2")

    assert restarted_client.resumed == [alice_id]
    assert restored == f"{alice_id}:A2"
    assert restarted_client.resumed_kwargs[0]["large_output"] == {
        "enabled": True,
        "max_size_bytes": 50 * 1024,
        "output_directory": str(
            tmp_path / ".copilot-data" / "session-state" / alice_id / "files"
        ),
    }

    bob_before = store.get(bob)
    new_alice_id = await restarted.new_session(alice)

    assert new_alice_id != alice_id
    assert store.get(alice).session_id == new_alice_id  # type: ignore[union-attr]
    assert store.get(bob) == bob_before
    store.close()


def test_same_user_different_group_and_thread_are_isolated(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    identity = config.relay.identity
    base = RelayRequest("user_message", "x", None, {"user_id": "alice", "chat_id": "g1"})
    other_group = RelayRequest(
        "user_message", "x", None, {"user_id": "alice", "chat_id": "g2"}
    )
    thread = RelayRequest(
        "user_message",
        "x",
        None,
        {"user_id": "alice", "chat_id": "g1", "thread_id": "topic"},
    )

    assert identity.mode == "message_fields"
    assert len(
        {
            base.conversation_key(config.relay),
            other_group.conversation_key(config.relay),
            thread.conversation_key(config.relay),
        }
    ) == 3
