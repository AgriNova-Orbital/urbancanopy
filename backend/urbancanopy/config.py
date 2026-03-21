from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

import yaml


CatalogProvider = Literal["copernicus", "opendatacube"]


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
    return RunConfig(
        name=raw["name"],
        focus_city=raw["focus_city"],
        comparison_cities=list(raw["comparison_cities"]),
        catalogs={
            key: cast(CatalogProvider, value) for key, value in raw["catalogs"].items()
        },
        summer_window={key: str(value) for key, value in raw["summer_window"].items()},
        hotspot_percentile=int(raw["hotspot_percentile"]),
        weights={key: float(value) for key, value in raw["weights"].items()},
        buffer_distances_m=[int(value) for value in raw["buffer_distances_m"]],
        comparison_ring_km=[int(value) for value in raw["comparison_ring_km"]],
        scenario_canopy_delta_pct=float(raw["scenario_canopy_delta_pct"]),
    )
