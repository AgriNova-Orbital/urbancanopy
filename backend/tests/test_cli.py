import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
import xarray as xr

from urbancanopy.cli import execute_pipeline, run_pipeline
from urbancanopy.event_store import EventStore

CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "multicity-demo.yml"


def _synthetic_boundary() -> gpd.GeoDataFrame:
    from shapely.geometry import box

    return gpd.GeoDataFrame(
        geometry=[box(121.5, 25.0, 121.6, 25.1)],
        crs="EPSG:4326",
    )


def _write_priority_geojson(zones: gpd.GeoDataFrame, path: Path, **_kwargs) -> None:
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


def test_run_pipeline_creates_backend_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "outputs"

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

    run_pipeline(
        config_path=CONFIG_PATH,
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

    run_pipeline(
        config_path=CONFIG_PATH,
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path,
        log_timestamp="2026-03-22_13-11-00",
    )

    event_log = tmp_path / "2026-03-22_13-11-00_events.db"
    from urbancanopy.event_store import EventStore

    store = EventStore(event_log)
    events = store.list_recent_events(limit=100)

    assert all(event["event"] != "dataset.probe.succeeded" for event in events)
    skipped_probe_events = [
        event for event in events if event["event"] == "dataset.probe.skipped"
    ]
    assert skipped_probe_events
    assert all(
        event["meta"]["status"] == "offline_demo_skip" for event in skipped_probe_events
    )
    capabilities_by_source = {
        event["meta"]["source_key"]: event["meta"]["capability"]
        for event in skipped_probe_events
    }
    transports_by_source = {
        event["meta"]["source_key"]: event["meta"]["actual_transport"]
        for event in skipped_probe_events
    }
    assert capabilities_by_source == {
        "sentinel2": "working_now",
        "sentinel3": "fallback_only",
        "landsat": "needs_fix",
    }
    assert transports_by_source == {
        "sentinel2": "planetary_computer_stac",
        "sentinel3": "not_implemented",
        "landsat": "planetary_computer_stac",
    }
    assert any(event["event"] == "fallback.activated" for event in events)


def test_run_pipeline_writes_real_offline_demo_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "outputs"
    config_path = CONFIG_PATH

    def _fail_if_live_called(*_args, **_kwargs):
        raise AssertionError("live catalog loading should stay disabled in demo mode")

    monkeypatch.setattr(
        "urbancanopy.sources.CopernicusStacClient.load", _fail_if_live_called
    )
    monkeypatch.setattr(
        "urbancanopy.sources.OpenDataCubeClient.load", _fail_if_live_called
    )
    monkeypatch.setattr(
        "urbancanopy.cli._load_city_boundary", lambda _city: _synthetic_boundary()
    )
    monkeypatch.setattr(
        "urbancanopy.cli.export_priority_zones", _write_priority_geojson
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

    priority_zones = json.loads(outputs["priority_geojson"].read_text(encoding="utf-8"))
    assert priority_zones["type"] == "FeatureCollection"
    assert priority_zones["features"]
    assert {"zone_id", "priority_score"}.issubset(
        priority_zones["features"][0]["properties"]
    )


def test_run_pipeline_offline_demo_logs_probe_skips_not_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "urbancanopy.cli._load_city_boundary", lambda _city: _synthetic_boundary()
    )
    monkeypatch.setattr(
        "urbancanopy.cli.export_priority_zones", _write_priority_geojson
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

    run_pipeline(
        config_path=CONFIG_PATH,
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path,
        log_timestamp="2026-03-22_14-10-00",
        mode="offline_demo",
    )

    store = EventStore(tmp_path / "2026-03-22_14-10-00_events.db")
    events = store.list_recent_events(limit=100)
    assert any(event["event"] == "dataset.probe.skipped" for event in events)
    assert not any(
        event["event"] == "dataset.probe.failed"
        and event["meta"].get("status") == "offline_demo_skip"
        for event in events
    )
    skipped_events = [
        event for event in events if event["event"] == "dataset.probe.skipped"
    ]
    assert skipped_events
    assert all(event["fallbackUsed"] is False for event in skipped_events)


def test_run_pipeline_offline_mode_skips_live_probing_and_uses_synthetic_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fail_if_live_called(*_args, **_kwargs):
        raise AssertionError(
            "live catalog loading should stay disabled in offline mode"
        )

    monkeypatch.setattr(
        "urbancanopy.sources.CopernicusStacClient.load", _fail_if_live_called
    )
    monkeypatch.setattr(
        "urbancanopy.sources.OpenDataCubeClient.load", _fail_if_live_called
    )
    monkeypatch.setattr(
        "urbancanopy.cli._load_city_boundary", lambda _city: _synthetic_boundary()
    )
    monkeypatch.setattr(
        "urbancanopy.cli.export_priority_zones", _write_priority_geojson
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

    outputs = run_pipeline(
        config_path=CONFIG_PATH,
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path,
        log_timestamp="2026-03-22_14-09-00",
        mode="offline",
    )

    store = EventStore(tmp_path / "2026-03-22_14-09-00_events.db")
    events = store.list_recent_events(limit=100)

    assert outputs["priority_geojson"].exists()
    assert any(event["event"] == "dataset.probe.skipped" for event in events)
    assert not any(event["event"] == "dataset.probe.succeeded" for event in events)
    assert not any(event["event"] == "dataset.probe.failed" for event in events)


def test_execute_pipeline_probe_only_attempts_live_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempted: list[tuple[str, str]] = []

    def _record_load(
        self, bbox=(0, 0, 0, 0), *, logger=None, run_id=None, mode="offline"
    ):
        attempted.append((self.source_key, mode))
        return xr.DataArray([1], dims=["x"])

    monkeypatch.setattr(
        "urbancanopy.cli._load_city_boundary", lambda _city: _synthetic_boundary()
    )
    monkeypatch.setattr("urbancanopy.sources.CopernicusStacClient.load", _record_load)
    monkeypatch.setattr("urbancanopy.sources.OpenDataCubeClient.load", _record_load)

    outputs = execute_pipeline(
        config_path=CONFIG_PATH,
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path,
        log_timestamp="2026-03-22_14-11-00",
        mode="live_probe",
        probe_only=True,
    )

    assert outputs == {}
    assert attempted
    assert all(mode == "live_probe" for _, mode in attempted)
    assert not (tmp_path / "outputs" / "priority_zones.geojson").exists()


def test_execute_pipeline_live_probe_requires_probe_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "urbancanopy.cli._load_city_boundary", lambda _city: _synthetic_boundary()
    )
    monkeypatch.setattr(
        "urbancanopy.sources.CopernicusStacClient.load",
        lambda self, bbox=(0, 0, 0, 0), **_kwargs: xr.DataArray([1], dims=["x"]),
    )
    monkeypatch.setattr(
        "urbancanopy.sources.OpenDataCubeClient.load",
        lambda self, bbox=(0, 0, 0, 0), **_kwargs: xr.DataArray([1], dims=["x"]),
    )

    def _unexpected_export(*_args, **_kwargs):
        raise AssertionError("live_probe should not generate synthetic outputs")

    monkeypatch.setattr("urbancanopy.cli.export_priority_zones", _unexpected_export)
    monkeypatch.setattr("urbancanopy.cli.export_city_comparison", _unexpected_export)
    monkeypatch.setattr("urbancanopy.cli.export_city_signature", _unexpected_export)
    monkeypatch.setattr("urbancanopy.cli.export_park_cooling", _unexpected_export)

    with pytest.raises(ValueError, match="live_probe mode requires --probe-only"):
        execute_pipeline(
            config_path=CONFIG_PATH,
            output_dir=tmp_path / "outputs",
            log_dir=tmp_path,
            log_timestamp="2026-03-22_14-11-30",
            mode="live_probe",
            probe_only=False,
        )


def test_execute_pipeline_offline_probe_only_stops_before_synthetic_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _unexpected_boundary(_city: str):
        raise AssertionError("offline probe-only run should not load boundaries")

    monkeypatch.setattr("urbancanopy.cli._load_city_boundary", _unexpected_boundary)

    def _unexpected_export(*_args, **_kwargs):
        raise AssertionError(
            "probe_only offline run should not generate synthetic outputs"
        )

    monkeypatch.setattr("urbancanopy.cli.export_priority_zones", _unexpected_export)
    monkeypatch.setattr("urbancanopy.cli.export_city_comparison", _unexpected_export)
    monkeypatch.setattr("urbancanopy.cli.export_city_signature", _unexpected_export)
    monkeypatch.setattr("urbancanopy.cli.export_park_cooling", _unexpected_export)

    outputs = execute_pipeline(
        config_path=CONFIG_PATH,
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path,
        log_timestamp="2026-03-22_14-11-40",
        mode="offline",
        probe_only=True,
    )

    store = EventStore(tmp_path / "2026-03-22_14-11-40_events.db")
    events = store.list_recent_events(limit=100)

    assert outputs == {}
    assert any(event["event"] == "dataset.probe.skipped" for event in events)
    assert not any(event["event"] == "fallback.activated" for event in events)


def test_execute_pipeline_probe_only_live_failures_do_not_activate_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "urbancanopy.cli._load_city_boundary", lambda _city: _synthetic_boundary()
    )
    monkeypatch.setattr(
        "urbancanopy.sources.CopernicusStacClient._search_items",
        lambda self, bbox: [],
    )
    monkeypatch.setattr(
        "urbancanopy.sources.OpenDataCubeClient._search_items",
        lambda self, bbox: [],
    )

    outputs = execute_pipeline(
        config_path=CONFIG_PATH,
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path,
        log_timestamp="2026-03-22_14-12-00",
        mode="live_probe",
        probe_only=True,
    )

    store = EventStore(tmp_path / "2026-03-22_14-12-00_events.db")
    events = store.list_recent_events(limit=100)

    assert outputs == {}
    assert any(event["event"] == "dataset.probe.failed" for event in events)
    assert not any(event["event"] == "fallback.activated" for event in events)


def test_cli_lifecycle_events_only_mark_fallback_used_after_demo_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "urbancanopy.cli._load_city_boundary", lambda _city: _synthetic_boundary()
    )
    monkeypatch.setattr(
        "urbancanopy.cli.export_priority_zones", _write_priority_geojson
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

    run_pipeline(
        config_path=CONFIG_PATH,
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path,
        log_timestamp="2026-03-22_14-13-00",
        mode="offline_demo",
    )

    store = EventStore(tmp_path / "2026-03-22_14-13-00_events.db")
    events = store.list_recent_events(limit=200)
    mode_changed = next(event for event in events if event["event"] == "mode.changed")
    pipeline_started = next(
        event for event in events if event["event"] == "pipeline.started"
    )
    pipeline_completed = next(
        event for event in events if event["event"] == "pipeline.completed"
    )

    assert mode_changed["fallbackUsed"] is False
    assert pipeline_started["fallbackUsed"] is False
    assert pipeline_completed["fallbackUsed"] is True


def test_methodology_documents_current_live_runtime_truth() -> None:
    text = (Path(__file__).resolve().parent.parent / "methodology.md").read_text(
        encoding="utf-8"
    )

    assert "live_success" in text
    assert "live_failure" in text
    assert "live_failure_fallback" in text
    assert "offline_demo_skip" in text
    assert "dataset.probe.succeeded" in text
    assert "dataset.probe.failed" in text
    assert "dataset.probe.skipped" in text
    assert "sentinel2: datasource `copernicus`, capability `working_now`" in text
    assert "sentinel3: datasource `copernicus`, capability `fallback_only`" in text
    assert "landsat: datasource `opendatacube`, capability `needs_fix`" in text
    assert "actual transport" in text.lower()
    assert (
        "python -m urbancanopy.cli --config configs/multicity-demo.yml --output-dir ../tmp/offline-demo --mode offline_demo"
        in text
    )
    assert (
        "python -m urbancanopy.cli --config configs/multicity-demo.yml --output-dir ../tmp/live-probe --mode live_probe --probe-only"
        in text
    )
    assert "`copernicus`: verify the Sentinel probe events honestly show" in text
    assert "`opendatacube`: verify the Landsat probe events still report" in text


def test_main_parses_mode_and_probe_only(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run_pipeline(**kwargs):
        captured.update(kwargs)
        return {}

    monkeypatch.setattr("urbancanopy.cli.run_pipeline", _fake_run_pipeline)
    monkeypatch.setattr(
        "sys.argv",
        [
            "urbancanopy.cli",
            "--config",
            str(CONFIG_PATH),
            "--output-dir",
            "tmp/live-probe",
            "--mode",
            "live_probe",
            "--probe-only",
        ],
    )

    from urbancanopy.cli import main

    main()

    assert captured["config_path"] == CONFIG_PATH
    assert captured["output_dir"] == Path("tmp/live-probe")
    assert captured["mode"] == "live_probe"
    assert captured["probe_only"] is True


def test_main_exits_for_live_probe_without_probe_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "urbancanopy.cli",
            "--config",
            str(CONFIG_PATH),
            "--output-dir",
            "tmp/live-probe",
            "--mode",
            "live_probe",
        ],
    )

    from urbancanopy.cli import main

    with pytest.raises(SystemExit, match="1"):
        main()


def test_execute_pipeline_raises_when_expected_export_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = CONFIG_PATH

    monkeypatch.setattr(
        "urbancanopy.cli.export_park_cooling", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "urbancanopy.cli._load_city_boundary", lambda _city: _synthetic_boundary()
    )
    monkeypatch.setattr(
        "urbancanopy.cli.export_priority_zones", _write_priority_geojson
    )

    with pytest.raises(FileNotFoundError, match="park_cooling.csv"):
        execute_pipeline(config_path=config_path, output_dir=tmp_path)
