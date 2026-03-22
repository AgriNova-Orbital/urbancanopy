import json
import sqlite3
from pathlib import Path
from typing import Any


class EventStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    @classmethod
    def create(cls, *, base_dir: Path, timestamp: str | None = None) -> "EventStore":
        filename = f"{timestamp}_events.db" if timestamp is not None else "events.db"
        store = cls(base_dir / filename)
        store.initialize()
        return store

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    level TEXT NOT NULL,
                    event TEXT NOT NULL,
                    component TEXT NOT NULL,
                    message TEXT NOT NULL,
                    run_id TEXT,
                    job_id TEXT,
                    mode TEXT,
                    online INTEGER,
                    fallback_used INTEGER NOT NULL,
                    meta_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    artifact_type TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    meta_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS dataset_probes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    dataset TEXT NOT NULL,
                    status TEXT NOT NULL,
                    checked_at TEXT NOT NULL,
                    meta_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    mode TEXT,
                    online INTEGER,
                    status TEXT,
                    meta_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )

    def append_event(self, event: dict[str, Any]) -> None:
        meta = event.get("meta") or {}
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO events (
                    ts,
                    level,
                    event,
                    component,
                    message,
                    run_id,
                    job_id,
                    mode,
                    online,
                    fallback_used,
                    meta_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["ts"],
                    event["level"],
                    event["event"],
                    event["component"],
                    event["message"],
                    event.get("runId"),
                    event.get("jobId"),
                    event.get("mode"),
                    self._encode_bool(event.get("online")),
                    self._encode_bool(event.get("fallbackUsed")) or 0,
                    json.dumps(meta),
                ),
            )

    def list_recent_events(self, limit: int) -> list[dict[str, Any]]:
        if limit <= 0:
            return []

        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT
                    ts,
                    level,
                    event,
                    component,
                    message,
                    run_id,
                    job_id,
                    mode,
                    online,
                    fallback_used,
                    meta_json
                FROM events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [self._decode_event(row) for row in rows]

    def _decode_event(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "ts": row["ts"],
            "level": row["level"],
            "event": row["event"],
            "component": row["component"],
            "message": row["message"],
            "runId": row["run_id"],
            "jobId": row["job_id"],
            "mode": row["mode"],
            "online": self._decode_bool(row["online"]),
            "fallbackUsed": bool(row["fallback_used"]),
            "meta": json.loads(row["meta_json"]),
        }

    @staticmethod
    def _encode_bool(value: bool | None) -> int | None:
        if value is None:
            return None
        return int(value)

    @staticmethod
    def _decode_bool(value: int | None) -> bool | None:
        if value is None:
            return None
        return bool(value)
