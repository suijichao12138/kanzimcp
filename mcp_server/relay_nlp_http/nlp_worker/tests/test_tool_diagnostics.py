import logging
from types import SimpleNamespace

from copilot.generated.session_events import (
    AssistantTurnRetryData,
    ToolExecutionCompleteData,
    ToolExecutionCompleteError,
    ToolExecutionCompleteResult,
    ToolExecutionStartData,
)

from copilot_runtime import ToolExecutionTracker


def start_event(
    call_id: str = "call-secret-id",
    *,
    name: str = "generic-mcp-tool",
    mcp_server: str | None = "kanzi-studio-mcp",
    mcp_tool: str | None = "kz_invoke",
) -> ToolExecutionStartData:
    return ToolExecutionStartData(
        tool_call_id=call_id,
        tool_name=name,
        mcp_server_name=mcp_server,
        mcp_tool_name=mcp_tool,
        turn_id="turn-1",
    )


def failure_event(
    *,
    call_id: str = "call-secret-id",
    code: str = "MCP_ERROR",
    message: str = "Kanzi request failed",
    result_content: str = "",
    mcp_meta=None,
) -> ToolExecutionCompleteData:
    return ToolExecutionCompleteData(
        success=False,
        tool_call_id=call_id,
        error=ToolExecutionCompleteError(code=code, message=message),
        result=ToolExecutionCompleteResult(content=result_content),
        mcp_meta=mcp_meta,
        turn_id="turn-1",
    )


def test_start_mapping_names_failure_without_exposing_only_call_id(caplog) -> None:
    tracker = ToolExecutionTracker("conversation-key", [])
    tracker.start(start_event())

    with caplog.at_level(logging.WARNING, logger="copilot_runtime"):
        tracker.complete(failure_event())

    messages = tracker.user_messages()
    assert messages == [
        "↪️ 工具 kanzi-studio-mcp/kz_invoke 本次调用未成功："
        "Kanzi request failed；Copilot 将继续处理"
    ]
    assert "call-secret-id" not in messages[0]
    assert "conversation-key" in caplog.text
    assert "call-secret-id" in caplog.text
    assert "kanzi-studio-mcp/kz_invoke" in caplog.text
    assert "MCP_ERROR" in caplog.text


def test_failure_logging_redacts_and_limits_sensitive_content(caplog) -> None:
    secret = "top-secret-value"
    tracker = ToolExecutionTracker("conversation-key", [secret])
    tracker.start(start_event())

    with caplog.at_level(logging.WARNING, logger="copilot_runtime"):
        tracker.complete(
            failure_event(
                message=f"Authorization: Bearer {secret}",
                result_content=f"token={secret} " + ("x" * 5000),
                mcp_meta={
                    "server": "kanzi",
                    "headers": {"Authorization": f"Bearer {secret}"},
                },
            )
        )

    assert secret not in caplog.text
    assert "******" in caplog.text
    assert "truncated" in caplog.text
    assert len(caplog.text) < 5000


def test_failure_logging_redacts_unknown_bearer_token(caplog) -> None:
    tracker = ToolExecutionTracker("conversation-key", [])
    tracker.start(start_event())

    with caplog.at_level(logging.WARNING, logger="copilot_runtime"):
        tracker.complete(
            failure_event(
                message="Authorization: Bearer not-in-config-token",
            )
        )

    assert "not-in-config-token" not in caplog.text
    assert "Bearer ******" in caplog.text or "Authorization: ******" in caplog.text


def test_cancelled_failure_is_logged_but_not_user_visible(caplog) -> None:
    tracker = ToolExecutionTracker("conversation-key", [])
    tracker.start(start_event())

    with caplog.at_level(logging.INFO, logger="copilot_runtime"):
        diagnostic = tracker.complete(
            failure_event(code="TOOL_CANCELLED", message="Request was cancelled")
        )

    assert diagnostic is not None
    assert diagnostic.classification == "cancelled"
    assert tracker.user_messages() == []
    assert '"classification": "cancelled"' in caplog.text


def test_assistant_retry_suppresses_nonfinal_failure() -> None:
    tracker = ToolExecutionTracker("conversation-key", [])
    tracker.start(start_event())
    tracker.complete(failure_event(message="temporary backend failure"))

    tracker.retry(
        AssistantTurnRetryData(
            turn_id="turn-1",
            reason="automatic model retry",
        )
    )

    assert tracker.user_messages() == []


def test_new_start_for_same_tool_marks_previous_failure_recovered() -> None:
    tracker = ToolExecutionTracker("conversation-key", [])
    tracker.start(start_event(call_id="call-1"))
    tracker.complete(failure_event(call_id="call-1"))

    tracker.start(start_event(call_id="call-2"))

    assert tracker.user_messages() == []


def test_permission_denial_uses_status_not_failure_warning() -> None:
    tracker = ToolExecutionTracker("conversation-key", [])
    tracker.start(start_event())
    tracker.complete(
        failure_event(
            code="PERMISSION_DENIED",
            message="Permission request was rejected",
        )
    )

    messages = tracker.user_messages()
    assert messages == [
        "🔒 工具 kanzi-studio-mcp/kz_invoke 本次未执行："
        "Permission request was rejected；Copilot 已继续处理本轮请求。"
    ]
    assert not messages[0].startswith("⚠️")


def test_interruption_suppresses_matching_failure() -> None:
    tracker = ToolExecutionTracker("conversation-key", [])
    tracker.start(start_event())
    tracker.complete(failure_event())

    tracker.interrupted(
        SimpleNamespace(
            tool_call_ids=["call-secret-id"],
            activity="tool",
        )
    )

    assert tracker.user_messages() == []


def test_successful_tool_never_generates_failure_message() -> None:
    tracker = ToolExecutionTracker("conversation-key", [])
    tracker.start(start_event())
    tracker.complete(
        ToolExecutionCompleteData(
            success=True,
            tool_call_id="call-secret-id",
            result=ToolExecutionCompleteResult(content="ok"),
            turn_id="turn-1",
        )
    )

    assert tracker.user_messages() == []
