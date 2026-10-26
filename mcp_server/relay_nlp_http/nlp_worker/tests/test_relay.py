import asyncio
import json

import pytest
from websockets.asyncio.server import serve

from copilot_runtime import RelayConfig, RelayIdentityConfig
from relay_client import RelayClient


@pytest.mark.asyncio
async def test_slot_registration_and_reconnect_reuses_exact_identity() -> None:
    registrations: list[dict[str, str]] = []
    registered_twice = asyncio.Event()

    async def handler(websocket) -> None:
        registrations.append(json.loads(await websocket.recv()))
        if len(registrations) >= 2:
            registered_twice.set()
        await websocket.close()

    async with serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        config = RelayConfig(
            url=f"ws://127.0.0.1:{port}/alice",
            channel="alice",
            allowed_channels={"alice"},
            identity=RelayIdentityConfig(
                mode="dedicated_channel",
                dedicated_principal_id="alice",
            ),
            reconnect_delay_seconds=0.01,
            ping_interval_seconds=0.05,
            ping_timeout_seconds=0.05,
        )
        client = RelayClient(config, lambda _raw: asyncio.sleep(0))
        task = asyncio.create_task(client.run())
        await asyncio.wait_for(registered_twice.wait(), timeout=2)
        await client.stop()
        await asyncio.wait_for(task, timeout=2)

    assert registrations[:2] == [
        {"role": "nlp_worker", "name": "alice"},
        {"role": "nlp_worker", "name": "alice"},
    ]
