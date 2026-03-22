import asyncio
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from urbancanopy.event_store import EventStore


def create_app(*, base_dir: Path) -> FastAPI:
    store = EventStore(_resolve_db_path(base_dir))
    store.initialize()
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

    @app.get("/api/events/stream")
    async def stream_events(request: Request) -> StreamingResponse:
        return StreamingResponse(
            _event_stream(request, store),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    return app


async def _event_stream(request: Request, store: EventStore):
    recent_events = list(reversed(store.list_recent_events(limit=20)))
    latest_event = recent_events[-1] if recent_events else None
    seen = {_event_key(event) for event in recent_events}

    yield _format_sse(
        "status",
        {
            "mode": _mode_for(latest_event),
            "status": _status_for(latest_event),
            "online": latest_event.get("online") if latest_event is not None else False,
        },
    )

    for event in recent_events:
        yield _format_sse("event", event)

    for _ in range(4):
        if await request.is_disconnected():
            break

        await asyncio.sleep(0.1)
        for event in reversed(store.list_recent_events(limit=20)):
            event_key = _event_key(event)
            if event_key in seen:
                continue
            seen.add(event_key)
            yield _format_sse("event", event)


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
        freshness_seconds = _freshness_seconds(row["created_at"])
        artifacts.append(
            {
                "artifactType": row["artifact_type"],
                "path": row["path"],
                "createdAt": row["created_at"],
                "status": _artifact_status(freshness_seconds),
                "freshnessSeconds": freshness_seconds,
                "isFresh": freshness_seconds <= 86400,
                "meta": _parse_json(row["meta_json"]),
            }
        )
    return artifacts


def _resolve_db_path(base_dir: Path) -> Path:
    candidates = sorted(
        base_dir.glob("*_events.db"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if candidates:
        return candidates[0]
    return base_dir / "events.db"


def _artifact_status(freshness_seconds: int) -> str:
    if freshness_seconds <= 86400:
        return "fresh"
    return "stale"


def _freshness_seconds(created_at: str) -> int:
    created_at_dt = datetime.fromisoformat(created_at)
    return max(
        0,
        int(
            (
                datetime.now(timezone.utc) - created_at_dt.astimezone(timezone.utc)
            ).total_seconds()
        ),
    )


def _read_scalar(db_path: Path, query: str) -> int:
    if not db_path.exists():
        return 0

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(query).fetchone()

    if row is None:
        return 0
    return int(row[0])


def _parse_json(value: str) -> dict[str, Any]:
    return json.loads(value)


def _format_sse(event_name: str, payload: dict[str, Any]) -> str:
    data = json.dumps(payload, separators=(",", ":"))
    return f"event: {event_name}\ndata: {data}\n\n"


def _event_key(event: dict[str, Any]) -> tuple[Any, ...]:
    return (
        event.get("ts"),
        event.get("event"),
        event.get("component"),
        event.get("message"),
    )
