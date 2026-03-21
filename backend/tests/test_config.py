from pathlib import Path

from urbancanopy.config import load_run_config


def test_load_run_config_supports_focus_and_comparison_cities(tmp_path: Path) -> None:
    config_path = tmp_path / "run.yml"
    config_path.write_text(
        """
name: multicity-demo
focus_city: taipei
comparison_cities: [taipei, tokyo, london, new_york]
catalogs:
  sentinel2: copernicus
  sentinel3: copernicus
  landsat: opendatacube
summer_window:
  start_date: 2025-06-01
  end_date: 2025-08-31
hotspot_percentile: 90
weights:
  lst: 0.5
  green: 0.3
  built: 0.2
buffer_distances_m: [0, 100, 300, 500]
comparison_ring_km: [0, 5, 20]
scenario_canopy_delta_pct: 10
""".strip()
    )

    cfg = load_run_config(config_path)

    assert cfg.focus_city == "taipei"
    assert cfg.comparison_cities == ["taipei", "tokyo", "london", "new_york"]
    assert cfg.catalogs["landsat"] == "opendatacube"
    assert cfg.comparison_ring_km == [0, 5, 20]


def test_load_run_config_normalizes_summer_window_dates_to_strings(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "run.yml"
    config_path.write_text(
        """
name: multicity-demo
focus_city: taipei
comparison_cities: [taipei, tokyo, london, new_york]
catalogs:
  sentinel2: copernicus
  sentinel3: copernicus
  landsat: opendatacube
summer_window:
  start_date: 2025-06-01
  end_date: 2025-08-31
hotspot_percentile: 90
weights:
  lst: 0.5
  green: 0.3
  built: 0.2
buffer_distances_m: [0, 100, 300, 500]
comparison_ring_km: [0, 5, 20]
scenario_canopy_delta_pct: 10
""".strip()
    )

    cfg = load_run_config(config_path)

    assert cfg.summer_window["start_date"] == "2025-06-01"
    assert isinstance(cfg.summer_window["start_date"], str)
    assert cfg.summer_window["end_date"] == "2025-08-31"
    assert isinstance(cfg.summer_window["end_date"], str)
