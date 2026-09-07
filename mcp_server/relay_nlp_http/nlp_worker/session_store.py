"""SQLite persistence for Copilot sessions and relay message deduplication."""

from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SessionMapping:
    conversation_key: str
    channel: str
    session_id: str
    model_name: str
    config_fingerprint: str
    status: str
    created_at: int
    updated_at: int
    last_error: str | None


class SessionStore:
    def __init__(self, path: Path, dedup_ttl_seconds: int = 86_400) -> None:
        self.path = path
        self.dedup_ttl_seconds = dedup_ttl_seconds
        self._connection: sqlite3.Connection | None = None
        self._lock = threading.RLock()

    def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS session_mappings (
                conversation_key TEXT PRIMARY KEY,
                channel TEXT NOT NULL,
                session_id TEXT NOT NULL,
                model_name TEXT NOT NULL,
                config_fingerprint TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                last_error TEXT
            );
            CREATE INDEX IF NOT EXISTS ix_session_mappings_channel
                ON session_mappings(channel);
            CREATE TABLE IF NOT EXISTS seen_events (
                event_id TEXT PRIMARY KEY,
                seen_at INTEGER NOT NULL
            );
            """
        )
        connection.commit()
        self._connection = connection

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("SessionStore.open() must be called first")
        return self._connection

    def close(self) -> None:
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    def get(self, conversation_key: str) -> SessionMapping | None:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM session_mappings WHERE conversation_key = ?",
                (conversation_key,),
            ).fetchone()
        return SessionMapping(**dict(row)) if row else None

    def put(
        self,
        conversation_key: str,
        channel: str,
        session_id: str,
        model_name: str,
        config_fingerprint: str,
        status: str = "active",
    ) -> None:
        now = int(time.time())
        with self._lock, self.connection:
            self.connection.execute(
                """
                INSERT INTO session_mappings(
                    conversation_key, channel, session_id, model_name,
                    config_fingerprint, status, created_at, updated_at, last_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
                ON CONFLICT(conversation_key) DO UPDATE SET
                    channel=excluded.channel,
                    session_id=excluded.session_id,
                    model_name=excluded.model_name,
                    config_fingerprint=excluded.config_fingerprint,
                    status=excluded.status,
                    updated_at=excluded.updated_at,
                    last_error=NULL
                """,
                (
                    conversation_key,
                    channel,
                    session_id,
                    model_name,
                    config_fingerprint,
                    status,
                    now,
                    now,
                ),
            )

    def set_status(
        self,
        conversation_key: str,
        status: str,
        last_error: str | None = None,
    ) -> None:
        with self._lock, self.connection:
            self.connection.execute(
                """
                UPDATE session_mappings
                SET status = ?, last_error = ?, updated_at = ?
                WHERE conversation_key = ?
                """,
                (status, last_error, int(time.time()), conversation_key),
            )

    def delete(self, conversation_key: str) -> None:
        with self._lock, self.connection:
            self.connection.execute(
                "DELETE FROM session_mappings WHERE conversation_key = ?",
                (conversation_key,),
            )

    def claim_event(self, event_id: str | None) -> bool:
        if not event_id:
            return True
        now = int(time.time())
        cutoff = now - self.dedup_ttl_seconds
        with self._lock, self.connection:
            self.connection.execute("DELETE FROM seen_events WHERE seen_at < ?", (cutoff,))
            cursor = self.connection.execute(
                "INSERT OR IGNORE INTO seen_events(event_id, seen_at) VALUES (?, ?)",
                (event_id, now),
            )
        return cursor.rowcount == 1

