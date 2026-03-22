from pathlib import Path

from fastapi.testclient import TestClient

from urbancanopy.status_api import create_app


def test_status_api_returns_last_update_and_recent_events(tmp_path: Path) -> None:
    app = create_app(base_dir=tmp_path)
    client = TestClient(app)

    response = client.get("/api/status")

    assert response.status_code == 200
    body = response.json()
    assert "lastUpdatedAt" in body
    assert "mode" in body
    assert "events" in body


def test_artifacts_api_returns_artifact_statuses(tmp_path: Path) -> None:
    app = create_app(base_dir=tmp_path)
    client = TestClient(app)

    response = client.get("/api/artifacts")

    assert response.status_code == 200
    body = response.json()
    assert "artifacts" in body
