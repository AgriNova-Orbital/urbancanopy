from pathlib import Path
from typing import Final

import geopandas as gpd
import pandas as pd


CITY_FIXTURES: Final[dict[str, str]] = {
    "taipei": "taipei.geojson",
    "tokyo": "tokyo.geojson",
    "london": "london.geojson",
    "new_york": "new_york.geojson",
}


def get_city_fixture_path(city: str) -> Path:
    return (
        Path(__file__).resolve().parent.parent
        / "tests"
        / "fixtures"
        / "cities"
        / CITY_FIXTURES[city]
    )


def build_comparison_zones(
    city_gdf: gpd.GeoDataFrame,
    *,
    inner_km: int,
    outer_km: int,
    exclude_core_to_km: int,
) -> gpd.GeoDataFrame:
    core = city_gdf.copy()
    core["zone"] = "urban_core"

    outer = city_gdf.copy()
    outer.geometry = city_gdf.buffer(outer_km * 1000).difference(
        city_gdf.buffer(exclude_core_to_km * 1000)
    )
    outer["zone"] = "outer_ring"

    return gpd.GeoDataFrame(
        pd.concat(
            [core[["zone", "geometry"]], outer[["zone", "geometry"]]], ignore_index=True
        ),
        crs=city_gdf.crs,
    )
