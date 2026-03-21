from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest

from urbancanopy.cli import execute_pipeline, run_pipeline


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
