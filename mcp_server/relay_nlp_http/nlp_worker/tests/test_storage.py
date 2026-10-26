from pathlib import Path

from session_store import SessionStore


def test_session_mapping_persists_across_reopen(tmp_path: Path) -> None:
    path = tmp_path / "bridge.db"
    first = SessionStore(path)
    first.open()
    first.put(
        "channel=test|principal=test",
        "test",
        "session-123",
        "model-x",
        "fingerprint-x",
    )
    first.close()

    second = SessionStore(path)
    second.open()
    mapping = second.get("channel=test|principal=test")
    second.close()

    assert mapping is not None
    assert mapping.session_id == "session-123"
    assert mapping.model_name == "model-x"
    assert mapping.config_fingerprint == "fingerprint-x"


def test_event_claim_is_idempotent(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "bridge.db")
    store.open()
    assert store.claim_event("message-1") is True
    assert store.claim_event("message-1") is False
    assert store.claim_event(None) is True
    store.close()
