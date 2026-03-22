from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest

from urbancanopy.cli import execute_pipeline, run_pipeline


def test_run_pipeline_creates_backend_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "outputs"

    from shapely.geometry import box

    monkeypatch.setattr(
        "urbancanopy.cli.export_priority_zones",
        lambda _df, path, **_kwargs: path.write_text("{}"),
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
        lambda _city: gpd.GeoDataFrame(
            geometry=[box(121.5, 25.0, 121.6, 25.1)], crs="EPSG:4326"
        ),
    )

    run_pipeline(
        config_path=Path("configs/multicity-demo.yml"),
        output_dir=output_dir,
        log_dir=tmp_path,
        log_timestamp="2026-03-22_12-45-00",
    )

    assert (tmp_path / "2026-03-22_12-45-00_back.log").exists()
    assert (tmp_path / "2026-03-22_12-45-00_back_debug.log").exists()
    assert (tmp_path / "2026-03-22_12-45-00_back_error.log").exists()


def test_run_pipeline_offline_demo_does_not_report_fake_probe_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from shapely.geometry import box

    monkeypatch.setattr(
        "urbancanopy.cli.export_priority_zones",
        lambda _df, path, **_kwargs: path.write_text("{}"),
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
        lambda _city: gpd.GeoDataFrame(
            geometry=[box(121.5, 25.0, 121.6, 25.1)], crs="EPSG:4326"
        ),
    )

    run_pipeline(
        config_path=Path("configs/multicity-demo.yml"),
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path,
        log_timestamp="2026-03-22_13-11-00",
    )

    event_log = tmp_path / "2026-03-22_13-11-00_events.db"
    from urbancanopy.event_store import EventStore

    store = EventStore(event_log)
    events = store.list_recent_events(limit=100)

    assert all(event["event"] != "dataset.probe.succeeded" for event in events)
    assert any(event["event"] == "dataset.probe.failed" for event in events)
    assert any(event["event"] == "fallback.activated" for event in events)


def test_run_pipeline_writes_real_offline_demo_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "outputs"
    config_path = (
        Path(__file__).resolve().parent.parent / "configs" / "multicity-demo.yml"
    )

    def _fail_if_live_called(*_args, **_kwargs):
        raise AssertionError("live catalog loading should stay disabled in demo mode")

    monkeypatch.setattr(
        "urbancanopy.sources.CopernicusStacClient.load", _fail_if_live_called
    )
    monkeypatch.setattr(
        "urbancanopy.sources.OpenDataCubeClient.load", _fail_if_live_called
    )

    outputs = run_pipeline(config_path=config_path, output_dir=output_dir)

    assert outputs["priority_geojson"].name == "priority_zones.geojson"
    assert outputs["city_comparison_csv"].name == "city_comparison.csv"
    assert outputs["city_signature_csv"].name == "city_signature.csv"
    assert outputs["park_cooling_csv"].name == "park_cooling.csv"

    for path in outputs.values():
        assert path.exists()

    city_comparison = pd.read_csv(outputs["city_comparison_csv"])
    assert city_comparison["city"].tolist() == ["taipei", "tokyo", "london", "new_york"]
    assert set(city_comparison.columns) == {"city", "heat_gap_c"}

    city_signature = pd.read_csv(outputs["city_signature_csv"])
    assert "taipei" in city_signature["city"].tolist()
    assert city_signature["signature_score"].is_monotonic_decreasing

    park_cooling = pd.read_csv(outputs["park_cooling_csv"])
    assert set(park_cooling.columns) == {
        "park_id",
        "delta_lst_c",
        "ci_low_c",
        "ci_high_c",
    }
    assert not park_cooling.empty

    priority_zones = gpd.read_file(outputs["priority_geojson"])
    assert not priority_zones.empty
    assert {"zone_id", "priority_score"}.issubset(priority_zones.columns)


def test_execute_pipeline_raises_when_expected_export_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = (
        Path(__file__).resolve().parent.parent / "configs" / "multicity-demo.yml"
    )

    monkeypatch.setattr(
        "urbancanopy.cli.export_park_cooling", lambda *_args, **_kwargs: None
    )

    with pytest.raises(FileNotFoundError, match="park_cooling.csv"):
        execute_pipeline(config_path=config_path, output_dir=tmp_path)
