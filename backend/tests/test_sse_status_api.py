import asyncio
from pathlib import Path
import threading
import time
from typing import Any, cast

from fastapi.routing import APIRoute

from urbancanopy.logger import UrbancanopyLogger
from urbancanopy.status_api import _event_stream, create_app


def test_events_stream_endpoint_exists(tmp_path) -> None:
    app = create_app(base_dir=tmp_path)

    route = next(
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/events/stream"
    )

    assert isinstance(route, APIRoute)
    assert "GET" in route.methods


def test_events_stream_includes_status_signal_and_recent_event(tmp_path: Path) -> None:
    logger = UrbancanopyLogger.create(
        base_dir=tmp_path,
        timestamp="2026-03-22_13-00-00",
    )
    logger.info(
        event="pipeline.completed",
        component="cli",
        message="pipeline finished",
        mode="offline_demo",
        online=False,
    )

    request = _RequestStub()
    frames = asyncio.run(
        _take_frames(_event_stream(cast(Any, request), logger.store), request, 2)
    )

    assert any(frame.startswith("event: status\n") for frame in frames)
    assert any('"mode":"offline_demo"' in frame for frame in frames)
    assert any('"status":"offline"' in frame for frame in frames)
    assert any(frame.startswith("event: event\n") for frame in frames)
    assert any('"event":"pipeline.completed"' in frame for frame in frames)


def test_events_stream_delivers_event_appended_after_connection_start(
    tmp_path: Path,
) -> None:
    logger = UrbancanopyLogger.create(
        base_dir=tmp_path,
        timestamp="2026-03-22_13-05-00",
    )
    request = _RequestStub()

    writer = threading.Thread(
        target=_append_event_after_delay,
        args=(logger, 0.6),
        kwargs={
            "event": "pipeline.completed",
            "component": "cli",
            "message": "pipeline finished later",
            "mode": "offline_demo",
            "online": False,
        },
    )
    writer.start()

    try:
        frames = asyncio.run(
            _take_frames(_event_stream(cast(Any, request), logger.store), request, 2)
        )
    finally:
        writer.join()

    assert any('"event":"pipeline.completed"' in frame for frame in frames)


def test_events_stream_emits_status_frame_for_later_connectivity_change(
    tmp_path: Path,
) -> None:
    logger = UrbancanopyLogger.create(
        base_dir=tmp_path,
        timestamp="2026-03-22_13-10-00",
    )
    logger.info(
        event="pipeline.started",
        component="cli",
        message="pipeline started",
        mode="offline_demo",
        online=False,
    )
    request = _RequestStub()

    writer = threading.Thread(
        target=_append_event_after_delay,
        args=(logger, 0.6),
        kwargs={
            "event": "connectivity.changed",
            "component": "sync",
            "message": "connection restored",
            "mode": "online",
            "online": True,
        },
    )
    writer.start()

    try:
        frames = asyncio.run(
            _take_frames(_event_stream(cast(Any, request), logger.store), request, 4)
        )
    finally:
        writer.join()

    assert sum(frame.startswith("event: status\n") for frame in frames) >= 2
    assert any('"event":"connectivity.changed"' in frame for frame in frames)
    assert any('"status":"online"' in frame for frame in frames)


def _append_event_after_delay(
    logger: UrbancanopyLogger,
    delay: float,
    *,
    event: str,
    component: str,
    message: str,
    mode: str,
    online: bool,
) -> None:
    time.sleep(delay)
    logger.info(
        event=event,
        component=component,
        message=message,
        mode=mode,
        online=online,
    )


class _RequestStub:
    def __init__(self) -> None:
        self.closed = False

    async def is_disconnected(self) -> bool:
        return self.closed


async def _take_frames(stream, request: _RequestStub, count: int) -> list[str]:
    frames: list[str] = []
    try:
        for _ in range(count):
            frames.append(await asyncio.wait_for(stream.__anext__(), timeout=2.0))
    finally:
        request.closed = True
        await stream.aclose()
    return frames
