from pathlib import Path

from urbancanopy.cli import run_pipeline


def test_run_pipeline_returns_focus_city_and_multicity_outputs(tmp_path: Path, monkeypatch) -> None:
    output_dir = tmp_path / "outputs"
    
    # Mock the internal execute_pipeline that actually runs the models
    monkeypatch.setattr(
        "urbancanopy.cli.execute_pipeline",
        lambda *_args, **_kwargs: {
            "priority_geojson": output_dir / "priority_zones.geojson",
            "city_comparison_csv": output_dir / "city_comparison.csv",
            "city_signature_csv": output_dir / "city_signature.csv",
            "park_cooling_csv": output_dir / "park_cooling.csv",
        },
    )

    # Use multicity-demo.yml from configs/
    config_path = Path(__file__).resolve().parent.parent / "configs" / "multicity-demo.yml"
    
    outputs = run_pipeline(config_path=config_path, output_dir=output_dir)

    assert outputs["priority_geojson"].name == "priority_zones.geojson"
    assert outputs["city_comparison_csv"].name == "city_comparison.csv"
    assert outputs["city_signature_csv"].name == "city_signature.csv"
    assert outputs["park_cooling_csv"].name == "park_cooling.csv"
