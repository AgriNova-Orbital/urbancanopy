from pathlib import Path

import pytest

from urbancanopy.config import load_run_config


VALID_CONFIG = """
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


def write_config(tmp_path: Path, contents: str) -> Path:
    config_path = tmp_path / "run.yml"
    config_path.write_text(contents)
    return config_path


def test_load_run_config_supports_focus_and_comparison_cities(tmp_path: Path) -> None:
    config_path = write_config(tmp_path, VALID_CONFIG)

    cfg = load_run_config(config_path)

    assert cfg.focus_city == "taipei"
    assert cfg.comparison_cities == ["taipei", "tokyo", "london", "new_york"]
    assert cfg.catalogs["landsat"] == "opendatacube"
    assert cfg.comparison_ring_km == [0, 5, 20]


def test_load_run_config_normalizes_summer_window_dates_to_strings(
    tmp_path: Path,
) -> None:
    config_path = write_config(tmp_path, VALID_CONFIG)

    cfg = load_run_config(config_path)

    assert cfg.summer_window["start_date"] == "2025-06-01"
    assert isinstance(cfg.summer_window["start_date"], str)
    assert cfg.summer_window["end_date"] == "2025-08-31"
    assert isinstance(cfg.summer_window["end_date"], str)


@pytest.mark.parametrize(
    ("config_text", "message"),
    [
        pytest.param(
            VALID_CONFIG.replace("focus_city: taipei", "focus_city: paris"),
            "focus_city must be one of the supported cities",
            id="unsupported-focus-city",
        ),
        pytest.param(
            VALID_CONFIG.replace(
                "comparison_cities: [taipei, tokyo, london, new_york]",
                "comparison_cities: [tokyo, london]",
            ),
            "focus_city must appear in comparison_cities",
            id="focus-city-missing-from-comparison-cities",
        ),
        pytest.param(
            VALID_CONFIG.replace(
                "catalogs:\n  sentinel2: copernicus\n  sentinel3: copernicus\n  landsat: opendatacube",
                "catalogs:\n  sentinel2: copernicus\n  landsat: opendatacube",
            ),
            "catalogs must contain exactly sentinel2, sentinel3, and landsat",
            id="missing-catalog-key",
        ),
        pytest.param(
            VALID_CONFIG.replace(
                "summer_window:\n  start_date: 2025-06-01\n  end_date: 2025-08-31",
                "summer_window:\n  start_date: 2025-08-31\n  end_date: 2025-06-01",
            ),
            "summer_window start_date must be on or before end_date",
            id="reversed-summer-window",
        ),
        pytest.param(
            VALID_CONFIG.replace("hotspot_percentile: 90", "hotspot_percentile: 101"),
            "hotspot_percentile must be between 1 and 100",
            id="hotspot-percentile-out-of-range",
        ),
        pytest.param(
            VALID_CONFIG.replace(
                "weights:\n  lst: 0.5\n  green: 0.3\n  built: 0.2",
                "weights:\n  lst: 0.5\n  green: 0.3\n  built: 0.3",
            ),
            "weights must sum to 1.0",
            id="weights-do-not-sum-to-one",
        ),
        pytest.param(
            VALID_CONFIG.replace(
                "buffer_distances_m: [0, 100, 300, 500]",
                "buffer_distances_m: [0, 300, 100]",
            ),
            "buffer_distances_m must be non-negative and sorted ascending",
            id="buffer-distances-unsorted",
        ),
        pytest.param(
            VALID_CONFIG.replace(
                "comparison_ring_km: [0, 5, 20]",
                "comparison_ring_km: [-1, 5, 20]",
            ),
            "comparison_ring_km must be non-negative and sorted ascending",
            id="comparison-rings-negative",
        ),
        pytest.param(
            VALID_CONFIG.replace(
                "scenario_canopy_delta_pct: 10",
                "scenario_canopy_delta_pct: -1",
            ),
            "scenario_canopy_delta_pct must be non-negative",
            id="negative-scenario-delta",
        ),
    ],
)
def test_load_run_config_rejects_invalid_semantic_values(
    tmp_path: Path,
    config_text: str,
    message: str,
) -> None:
    config_path = write_config(tmp_path, config_text)

    with pytest.raises(ValueError, match=message):
        load_run_config(config_path)
