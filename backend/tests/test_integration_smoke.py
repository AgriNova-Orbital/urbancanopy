import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from urbancanopy.cli import run_pipeline
from urbancanopy.config import load_run_config
from urbancanopy.event_store import EventStore
from urbancanopy.status_api import create_app


def _synthetic_boundary():
    from shapely.geometry import box
    import geopandas as gpd

    return gpd.GeoDataFrame(
        geometry=[box(121.5, 25.0, 121.6, 25.1)],
        crs="EPSG:4326",
    )


def _write_priority_geojson(zones, path: Path, **_kwargs) -> None:
    features = []
    zone_ids = zones.get("zone_id")
    if zone_ids is None:
        zone_ids = [f"zone-{index}" for index in range(1, len(zones) + 1)]

    for geometry, zone_id, priority_score in zip(
        zones.geometry,
        zone_ids,
        zones["priority_score"],
        strict=False,
    ):
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "zone_id": zone_id,
                    "priority_score": float(priority_score),
                },
                "geometry": geometry.__geo_interface__,
            }
        )

    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}),
        encoding="utf-8",
    )


@pytest.mark.integration
def test_multicity_demo_config_is_well_formed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(Path(__file__).resolve().parent.parent)

    cfg = load_run_config("configs/multicity-demo.yml")

    assert cfg.focus_city == "taipei"
    assert cfg.comparison_cities == ["taipei", "tokyo", "london", "new_york"]


@pytest.mark.integration
def test_offline_pipeline_smoke_creates_root_logs_event_db_and_status_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend_dir = Path(__file__).resolve().parent.parent
    repo_root = backend_dir.parent
    log_dir = repo_root / "logs"
    timestamp = "2026-03-22_23-12-00"
    log_paths = [
        log_dir / f"{timestamp}_back.log",
        log_dir / f"{timestamp}_back_debug.log",
        log_dir / f"{timestamp}_back_error.log",
        log_dir / f"{timestamp}_events.db",
    ]

    monkeypatch.setattr(
        "urbancanopy.cli.export_priority_zones",
        _write_priority_geojson,
    )
    monkeypatch.setattr(
        "urbancanopy.cli.export_city_comparison",
        lambda df, path, **_kwargs: df.to_csv(path, index=False),
    )
    monkeypatch.setattr(
        "urbancanopy.cli.export_city_signature",
        lambda df, path, **_kwargs: df.to_csv(path, index=False),
    )
    monkeypatch.setattr(
        "urbancanopy.cli.export_park_cooling",
        lambda df, path, **_kwargs: df.to_csv(path, index=False),
    )
    monkeypatch.setattr(
        "urbancanopy.cli._load_city_boundary",
        lambda _city: _synthetic_boundary(),
    )

    for path in log_paths:
        path.unlink(missing_ok=True)

    try:
        run_pipeline(
            config_path=backend_dir / "configs" / "multicity-demo.yml",
            output_dir=tmp_path / "outputs",
            log_timestamp=timestamp,
        )

        for path in log_paths:
            assert path.exists()

        info_log = log_paths[0].read_text(encoding="utf-8")
        debug_log = log_paths[1].read_text(encoding="utf-8")
        error_log = log_paths[2].read_text(encoding="utf-8")
        assert "pipeline.completed" in info_log
        assert "dataset.probe.failed" in error_log
        assert "fallback.activated" in debug_log

        store = EventStore(log_paths[3])
        events = store.list_recent_events(limit=20)
        assert any(event["event"] == "pipeline.completed" for event in events)
        assert any(event["event"] == "fallback.activated" for event in events)

        client = TestClient(create_app(base_dir=log_dir))
        response = client.get("/api/status")

        assert response.status_code == 200
        body = response.json()
        assert body["mode"] == "offline_demo"
        assert body["status"] == "degraded"
        assert body["lastUpdatedAt"] is not None
        assert body["queueDepth"] == 0
        assert any(event["event"] == "pipeline.completed" for event in body["events"])
    finally:
        for path in log_paths:
            path.unlink(missing_ok=True)
