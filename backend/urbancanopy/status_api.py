import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from urbancanopy.event_store import EventStore


def create_app(*, base_dir: Path) -> FastAPI:
    store = EventStore.create(base_dir=base_dir)
    app = FastAPI()

    @app.get("/api/status")
    def get_status() -> dict[str, Any]:
        events = store.list_recent_events(limit=20)
        latest_event = events[0] if events else None
        return {
            "mode": _mode_for(latest_event),
            "status": _status_for(latest_event),
            "lastUpdatedAt": latest_event["ts"] if latest_event is not None else None,
            "queueDepth": _queue_depth_for(store.db_path),
            "events": events,
        }

    @app.get("/api/artifacts")
    def get_artifacts() -> dict[str, Any]:
        return {"artifacts": _list_artifacts(store.db_path)}

    return app


def _mode_for(latest_event: dict[str, Any] | None) -> str:
    if latest_event is None:
        return "offline"
    return str(latest_event.get("mode") or "offline")


def _status_for(latest_event: dict[str, Any] | None) -> str:
    if latest_event is None:
        return "offline"
    if latest_event.get("fallbackUsed"):
        return "degraded"
    if latest_event.get("online") is True:
        return "online"
    return "offline"


def _queue_depth_for(db_path: Path) -> int:
    return _read_scalar(
        db_path,
        "SELECT COUNT(*) FROM sync_state WHERE key LIKE 'queue.%' AND value NOT IN ('0', '', '[]', '{}')",
    )


def _list_artifacts(db_path: Path) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT artifact_type, path, created_at, meta_json
            FROM artifacts
            ORDER BY id DESC
            """
        ).fetchall()

    artifacts: list[dict[str, Any]] = []
    for row in rows:
        artifacts.append(
            {
                "artifactType": row["artifact_type"],
                "path": row["path"],
                "createdAt": row["created_at"],
                "status": "fresh",
                "meta": _parse_json(row["meta_json"]),
            }
        )
    return artifacts


def _read_scalar(db_path: Path, query: str) -> int:
    if not db_path.exists():
        return 0

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(query).fetchone()

    if row is None:
        return 0
    return int(row[0])


def _parse_json(value: str) -> dict[str, Any]:
    import json

    return json.loads(value)
