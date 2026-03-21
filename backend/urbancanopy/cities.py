from importlib.resources import files
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


def get_city_fixture_path(city: str, *, base_path: str | Path | None = None) -> Path:
    if city not in CITY_FIXTURES:
        raise ValueError(f"Unsupported city: {city}")

    if base_path is not None:
        city_base_path = Path(base_path)
    else:
        city_base_path = Path(str(files("urbancanopy.data.cities")))

    return city_base_path / CITY_FIXTURES[city]


def build_comparison_zones(
    city_gdf: gpd.GeoDataFrame,
    *,
    inner_km: int,
    outer_km: int,
    exclude_core_to_km: int,
) -> gpd.GeoDataFrame:
    source_crs = city_gdf.crs
    working_gdf = city_gdf

    if source_crs is not None and source_crs.is_geographic:
        projected_crs = city_gdf.estimate_utm_crs()
        if projected_crs is not None:
            working_gdf = city_gdf.to_crs(projected_crs)

    core = working_gdf.copy()
    if inner_km > 0:
        core.geometry = working_gdf.buffer(inner_km * 1000)
    core["zone"] = "urban_core"

    outer = working_gdf.copy()
    outer.geometry = working_gdf.buffer(outer_km * 1000).difference(
        working_gdf.buffer(exclude_core_to_km * 1000)
    )
    outer["zone"] = "outer_ring"

    zones = gpd.GeoDataFrame(
        pd.concat(
            [core[["zone", "geometry"]], outer[["zone", "geometry"]]], ignore_index=True
        ),
        crs=working_gdf.crs,
    )

    if source_crs is not None and zones.crs != source_crs:
        return zones.to_crs(source_crs)

    return zones
