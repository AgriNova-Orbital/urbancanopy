import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from urbancanopy.logger import UrbancanopyLogger
from urbancanopy.status_api import create_app


def test_status_api_returns_last_update_and_recent_events(tmp_path: Path) -> None:
    logger = UrbancanopyLogger.create(
        base_dir=tmp_path,
        timestamp="2026-03-22_12-45-00",
    )
    logger.info(
        event="pipeline.completed",
        component="cli",
        message="pipeline finished",
        run_id="run-1",
        mode="offline_demo",
        online=False,
    )

    app = create_app(base_dir=tmp_path)
    client = TestClient(app)

    response = client.get("/api/status")

    assert response.status_code == 200
    body = response.json()
    assert body["lastUpdatedAt"] is not None
    assert body["mode"] == "offline_demo"
    assert body["events"][0]["event"] == "pipeline.completed"


def test_artifacts_api_returns_artifact_statuses(tmp_path: Path) -> None:
    logger = UrbancanopyLogger.create(
        base_dir=tmp_path,
        timestamp="2026-03-22_12-45-00",
    )
    with sqlite3.connect(logger.store.db_path) as connection:
        connection.execute(
            """
            INSERT INTO artifacts (run_id, artifact_type, path, created_at, meta_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "run-1",
                "priority_zones",
                str(tmp_path / "priority_zones.geojson"),
                "2000-01-01T00:00:00+00:00",
                '{"source": "cache"}',
            ),
        )

    app = create_app(base_dir=tmp_path)
    client = TestClient(app)

    response = client.get("/api/artifacts")

    assert response.status_code == 200
    body = response.json()
    artifact = body["artifacts"][0]
    assert artifact["artifactType"] == "priority_zones"
    assert artifact["status"] == "stale"
    assert artifact["freshnessSeconds"] > 0
