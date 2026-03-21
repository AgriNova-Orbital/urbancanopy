from pathlib import Path
import geopandas as gpd
import pandas as pd

def export_priority_zones(zones: gpd.GeoDataFrame, path: Path | str) -> None:
    # Ensure EPSG:4326 for GeoJSON standard
    if zones.crs is not None and zones.crs != "EPSG:4326":
        export_gdf = zones.to_crs("EPSG:4326")
    else:
        export_gdf = zones
    export_gdf.to_file(path, driver="GeoJSON")

def export_city_comparison(df: pd.DataFrame, path: Path | str) -> None:
    df.to_csv(path, index=False)

def export_city_signature(df: pd.DataFrame, path: Path | str) -> None:
    df.to_csv(path, index=False)

def export_park_cooling(df: pd.DataFrame, path: Path | str) -> None:
    df.to_csv(path, index=False)
