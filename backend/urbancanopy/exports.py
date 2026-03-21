from pathlib import Path

import geopandas as gpd
import pandas as pd


def _validate_columns(
    frame: pd.DataFrame, required: set[str], export_name: str
) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        missing_columns = ", ".join(missing)
        raise ValueError(f"{export_name} missing required columns: {missing_columns}")


def _ensure_zone_ids(zones: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if "zone_id" in zones.columns:
        return zones

    return zones.assign(zone_id=[f"zone-{index}" for index in range(1, len(zones) + 1)])


def export_priority_zones(zones: gpd.GeoDataFrame, path: Path | str) -> None:
    _validate_columns(zones, {"geometry", "priority_score"}, "priority_zones.geojson")

    if zones.crs is None:
        raise ValueError(
            "priority_zones.geojson requires a defined CRS for EPSG:4326 export"
        )

    export_gdf = _ensure_zone_ids(zones)
    if export_gdf.crs != "EPSG:4326":
        export_gdf = export_gdf.to_crs("EPSG:4326")

    export_gdf.to_file(path, driver="GeoJSON")


def export_city_comparison(df: pd.DataFrame, path: Path | str) -> None:
    _validate_columns(df, {"city", "heat_gap_c"}, "city_comparison.csv")
    df.to_csv(path, index=False)


def export_city_signature(df: pd.DataFrame, path: Path | str) -> None:
    _validate_columns(
        df,
        {"city", "heat_gap_c", "mean_ndvi", "mean_ndbi", "signature_score"},
        "city_signature.csv",
    )
    df.to_csv(path, index=False)


def export_park_cooling(df: pd.DataFrame, path: Path | str) -> None:
    _validate_columns(
        df,
        {"park_id", "delta_lst_c", "ci_low_c", "ci_high_c"},
        "park_cooling.csv",
    )
    df.to_csv(path, index=False)
