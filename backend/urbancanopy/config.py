from dataclasses import dataclass
from datetime import date
from math import isclose
from pathlib import Path
from typing import Literal, cast

import yaml

from urbancanopy.cities import CITY_FIXTURES


CatalogProvider = Literal["copernicus", "opendatacube"]

SUPPORTED_CITIES = set(CITY_FIXTURES)
REQUIRED_CATALOGS = {"sentinel2", "sentinel3", "landsat"}
SUPPORTED_CATALOG_PROVIDERS = {"copernicus", "opendatacube"}
REQUIRED_CATALOG_PROVIDERS = {
    "sentinel2": "copernicus",
    "sentinel3": "copernicus",
    "landsat": "opendatacube",
}
REQUIRED_WEIGHTS = {"lst", "green", "built"}


@dataclass(slots=True)
class RunConfig:
    name: str
    focus_city: str
    comparison_cities: list[str]
    catalogs: dict[str, CatalogProvider]
    summer_window: dict[str, str]
    hotspot_percentile: int
    weights: dict[str, float]
    buffer_distances_m: list[int]
    comparison_ring_km: list[int]
    scenario_canopy_delta_pct: float


def load_run_config(path: str | Path) -> RunConfig:
    raw = yaml.safe_load(Path(path).read_text())
    comparison_cities = list(raw["comparison_cities"])
    catalogs: dict[str, CatalogProvider] = {
        key: cast(CatalogProvider, value) for key, value in raw["catalogs"].items()
    }
    summer_window = {key: str(value) for key, value in raw["summer_window"].items()}
    hotspot_percentile = int(raw["hotspot_percentile"])
    weights = {key: float(value) for key, value in raw["weights"].items()}
    buffer_distances_m = [int(value) for value in raw["buffer_distances_m"]]
    comparison_ring_km = [int(value) for value in raw["comparison_ring_km"]]
    scenario_canopy_delta_pct = float(raw["scenario_canopy_delta_pct"])

    validate_run_config(
        focus_city=raw["focus_city"],
        comparison_cities=comparison_cities,
        catalogs=catalogs,
        summer_window=summer_window,
        hotspot_percentile=hotspot_percentile,
        weights=weights,
        buffer_distances_m=buffer_distances_m,
        comparison_ring_km=comparison_ring_km,
        scenario_canopy_delta_pct=scenario_canopy_delta_pct,
    )

    return RunConfig(
        name=raw["name"],
        focus_city=raw["focus_city"],
        comparison_cities=comparison_cities,
        catalogs=catalogs,
        summer_window=summer_window,
        hotspot_percentile=hotspot_percentile,
        weights=weights,
        buffer_distances_m=buffer_distances_m,
        comparison_ring_km=comparison_ring_km,
        scenario_canopy_delta_pct=scenario_canopy_delta_pct,
    )


def validate_run_config(
    *,
    focus_city: str,
    comparison_cities: list[str],
    catalogs: dict[str, CatalogProvider],
    summer_window: dict[str, str],
    hotspot_percentile: int,
    weights: dict[str, float],
    buffer_distances_m: list[int],
    comparison_ring_km: list[int],
    scenario_canopy_delta_pct: float,
) -> None:
    if focus_city not in SUPPORTED_CITIES:
        raise ValueError("focus_city must be one of the supported cities")

    if not comparison_cities:
        raise ValueError("comparison_cities must be non-empty")

    unsupported_comparison_cities = sorted(
        city for city in comparison_cities if city not in SUPPORTED_CITIES
    )
    if unsupported_comparison_cities:
        raise ValueError("comparison_cities must contain only supported cities")

    if focus_city not in comparison_cities:
        raise ValueError("focus_city must appear in comparison_cities")

    if set(catalogs) != REQUIRED_CATALOGS:
        raise ValueError(
            "catalogs must contain exactly sentinel2, sentinel3, and landsat"
        )

    if any(
        provider not in SUPPORTED_CATALOG_PROVIDERS for provider in catalogs.values()
    ):
        raise ValueError("catalogs must use only supported providers")

    if any(
        catalogs[source] != provider
        for source, provider in REQUIRED_CATALOG_PROVIDERS.items()
    ):
        raise ValueError("catalogs must map each source to its required provider")

    if set(summer_window) != {"start_date", "end_date"}:
        raise ValueError("summer_window must contain start_date and end_date")

    start_date = date.fromisoformat(summer_window["start_date"])
    end_date = date.fromisoformat(summer_window["end_date"])
    if start_date > end_date:
        raise ValueError("summer_window start_date must be on or before end_date")

    if not 1 <= hotspot_percentile <= 100:
        raise ValueError("hotspot_percentile must be between 1 and 100")

    if set(weights) != REQUIRED_WEIGHTS:
        raise ValueError("weights must contain exactly lst, green, and built")

    if any(weight < 0.0 or weight > 1.0 for weight in weights.values()):
        raise ValueError("weights values must be between 0.0 and 1.0")

    if not isclose(sum(weights.values()), 1.0, abs_tol=1e-9):
        raise ValueError("weights must sum to 1.0")

    validate_non_negative_sorted_sequence(
        "buffer_distances_m",
        buffer_distances_m,
    )
    validate_non_negative_sorted_sequence(
        "comparison_ring_km",
        comparison_ring_km,
    )

    if scenario_canopy_delta_pct < 0:
        raise ValueError("scenario_canopy_delta_pct must be non-negative")


def validate_non_negative_sorted_sequence(name: str, values: list[int]) -> None:
    if any(value < 0 for value in values) or values != sorted(values):
        raise ValueError(f"{name} must be non-negative and sorted ascending")
