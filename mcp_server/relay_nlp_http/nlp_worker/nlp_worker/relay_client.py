"""Existing relay_multi.py slot registration, messages, heartbeat, and reconnect."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection
from websockets.exceptions import ConnectionClosed

log = logging.getLogger(__name__)

ACCEPTED_INPUT_TYPES = {"user_message", "user_choice"}
IGNORED_INPUT_TYPES = {"connected", "mcp_response", "server_disconnected"}


class RelayMessageError(ValueError):
    """Invalid or unsupported relay message."""


@dataclass(frozen=True, slots=True)
class RelayRequest:
    message_type: str
    text: str
    message_id: str | None
    fields: dict[str, str]

    def conversation_key(self, relay_config: Any) -> str:
        identity = relay_config.identity
        if identity.mode == "dedicated_channel":
            return (
                f"channel={relay_config.channel}|"
                f"principal={identity.dedicated_principal_id}"
            )
        upstream_session = self.fields.get("session_id")
        if upstream_session:
            return f"channel={relay_config.channel}|session_id={upstream_session}"
        user_id = self.fields.get("user_id")
        chat_id = self.fields.get("chat_id")
        if not user_id or not chat_id:
            raise RelayMessageError(
                "message_fields isolation requires both user_id and chat_id"
            )
        parts = [
            f"channel={relay_config.channel}",
            f"chat_id={chat_id}",
            f"user_id={user_id}",
        ]
        if identity.include_thread_scope:
            scope = self.fields.get("thread_id") or self.fields.get("root_id") or "chat"
            parts.append(f"scope={scope}")
        return "|".join(parts)


def parse_relay_message(raw: str) -> RelayRequest | None:
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RelayMessageError("relay message is not valid JSON") from exc
    if not isinstance(data, dict):
        raise RelayMessageError("relay message must be a JSON object")
    message_type = data.get("type")
    if message_type in IGNORED_INPUT_TYPES:
        return None
    if message_type not in ACCEPTED_INPUT_TYPES:
        raise RelayMessageError(f"unsupported relay message type: {message_type!r}")
    text = data.get("selected") or data.get("text")
    if not isinstance(text, str) or not text.strip():
        raise RelayMessageError("relay user message requires non-empty text/selected")
    fields: dict[str, str] = {}
    for name in (
        "user_id",
        "chat_id",
        "chat_type",
        "session_id",
        "thread_id",
        "root_id",
    ):
        value = data.get(name)
        if value is not None:
            fields[name] = str(value)
    message_id = next(
        (
            str(data[name])
            for name in ("message_id", "event_id", "request_id")
            if data.get(name)
        ),
        None,
    )
    return RelayRequest(message_type, text.strip(), message_id, fields)


def output_message(
    text: str,
    output_type: str = "claude_output",
    request: RelayRequest | None = None,
) -> dict[str, str]:
    result = {"type": output_type, "text": text}
    if request is not None:
        if request.message_id:
            result["request_id"] = request.message_id
        result.update(request.fields)
    return result


def thinking_message(text: str) -> dict[str, str]:
    return {"type": "thinking", "text": text}


class RelayClient:
    def __init__(
        self,
        config: Any,
        on_message: Callable[[str], Awaitable[None]],
    ) -> None:
        self.config = config
        self.on_message = on_message
        self.websocket: ClientConnection | None = None
        self.running = False
        self.connected = asyncio.Event()
        self._send_lock = asyncio.Lock()

    async def run(self) -> None:
        self.running = True
        while self.running:
            try:
                async with websockets.connect(
                    self.config.url,
                    ping_interval=self.config.ping_interval_seconds,
                    ping_timeout=self.config.ping_timeout_seconds,
                    close_timeout=5,
                    max_size=self.config.max_message_bytes,
                ) as websocket:
                    self.websocket = websocket
                    await websocket.send(
                        json.dumps(
                            {"role": self.config.role, "name": self.config.channel},
                            ensure_ascii=False,
                        )
                    )
                    self.connected.set()
                    log.info("Connected to relay: %s", self.config.url)
                    async for raw in websocket:
                        if isinstance(raw, bytes):
                            log.warning("Ignoring binary relay message")
                            continue
                        await self.on_message(raw)
            except (ConnectionClosed, OSError, TimeoutError) as exc:
                if self.running:
                    log.warning("Relay disconnected: %s", exc)
            finally:
                self.websocket = None
                self.connected.clear()
            if self.running:
                await asyncio.sleep(self.config.reconnect_delay_seconds)

    async def send(self, message: dict[str, object]) -> None:
        websocket = self.websocket
        if websocket is None:
            raise ConnectionError("relay is not connected")
        async with self._send_lock:
            await websocket.send(json.dumps(message, ensure_ascii=False))

    async def stop(self) -> None:
        self.running = False
        if self.websocket is not None:
            await self.websocket.close()
