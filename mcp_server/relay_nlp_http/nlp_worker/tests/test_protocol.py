import json

import pytest

from copilot_runtime import RelayConfig, RelayIdentityConfig
from nlp_worker import parse_command, split_message
from relay_client import (
    RelayMessageError,
    output_message,
    parse_relay_message,
    thinking_message,
)


def relay_config(**changes) -> RelayConfig:
    values = {
        "url": "ws://localhost:58080/test",
        "channel": "test",
        "allowed_channels": {"test"},
        "identity": RelayIdentityConfig(
            mode="dedicated_channel",
            dedicated_principal_id="test-user",
        ),
    }
    values.update(changes)
    return RelayConfig(**values)


def test_legacy_relay_contract_round_trip() -> None:
    request = parse_relay_message(
        json.dumps({"type": "user_message", "text": "创建按钮"}, ensure_ascii=False)
    )

    assert request is not None
    assert request.text == "创建按钮"
    assert request.conversation_key(relay_config()) == (
        "channel=test|principal=test-user"
    )
    assert thinking_message("处理中") == {"type": "thinking", "text": "处理中"}
    assert output_message("完成") == {"type": "claude_output", "text": "完成"}


def test_future_identity_fields_can_form_session_key() -> None:
    request = parse_relay_message(
        json.dumps(
            {
                "type": "user_message",
                "text": "hello",
                "chat_id": "chat-1",
                "thread_id": "thread-2",
                "message_id": "msg-3",
            }
        )
    )
    config = relay_config(
        identity=RelayIdentityConfig(mode="message_fields")
    )

    assert request is not None
    request.fields["user_id"] = "user-1"
    assert request.conversation_key(config) == (
        "channel=test|chat_id=chat-1|user_id=user-1|scope=thread-2"
    )
    assert request.message_id == "msg-3"
    assert output_message("done", request=request) == {
        "type": "claude_output",
        "text": "done",
        "request_id": "msg-3",
        "chat_id": "chat-1",
        "thread_id": "thread-2",
        "user_id": "user-1",
    }


def test_missing_configured_identity_is_explicit() -> None:
    request = parse_relay_message('{"type":"user_message","text":"hello"}')
    assert request is not None
    with pytest.raises(RelayMessageError, match="user_id"):
        request.conversation_key(
            relay_config(identity=RelayIdentityConfig(mode="message_fields"))
        )


@pytest.mark.parametrize("text,name", [
    ("/new", "new"),
    ("/status", "status"),
    ("/cancel", "cancel"),
    ("/help", "help"),
])
def test_command_parser(text: str, name: str) -> None:
    command = parse_command(text)
    assert command is not None
    assert command.name == name


def test_message_split_is_lossless() -> None:
    text = "第一段。\n第二段很长。" * 30
    chunks = split_message(text, 100)
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert "".join(chunks).replace("\n", "") == text.replace("\n", "")
