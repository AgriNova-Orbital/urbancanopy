from pathlib import Path

from fastapi.testclient import TestClient

from urbancanopy.logger import UrbancanopyLogger
from urbancanopy.status_api import create_app


def test_events_stream_endpoint_exists(tmp_path) -> None:
    app = create_app(base_dir=tmp_path)
    client = TestClient(app)

    response = client.get("/api/events/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")


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

    app = create_app(base_dir=tmp_path)
    client = TestClient(app)

    response = client.get("/api/events/stream")

    assert response.status_code == 200
    assert "event: status" in response.text
    assert '"mode":"offline_demo"' in response.text
    assert '"status":"offline"' in response.text
    assert "event: event" in response.text
    assert '"event":"pipeline.completed"' in response.text
