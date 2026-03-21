import numpy as np
import pandas as pd
import pytest
import xarray as xr
import geopandas as gpd
from shapely.geometry import Polygon

from urbancanopy.cities import build_comparison_zones
from urbancanopy.comparison import summarize_city_heat_gap
from urbancanopy.modeling import build_city_signature_table
from urbancanopy.scoring import priority_score
from urbancanopy.vectorize import vectorize_priority_cells
from urbancanopy.aggregation import aggregate_city_metrics
from urbancanopy.parks import pci_summary

def test_offline_pipeline_produces_exportable_artifacts() -> None:
    # 1. City Comparison & Signature
    city = gpd.GeoDataFrame(
        {"city": ["taipei"]},
        geometry=[Polygon([(121.50, 25.02), (121.54, 25.02), (121.54, 25.06), (121.50, 25.06)])],
        crs="EPSG:4326",
    )
    zones = build_comparison_zones(city, inner_km=1, outer_km=5, exclude_core_to_km=2)
    
    # Mock some temperature samples for comparison
    samples = pd.DataFrame({
        "city": ["taipei", "taipei"],
        "zone": ["urban_core", "outer_ring"],
        "lst_c": [35.0, 32.0]
    })
    
    comparison_df = summarize_city_heat_gap(samples)
    assert comparison_df.loc[0, "heat_gap_c"] == 3.0
    
    # Mock some NDVIs for aggregation
    ndvi = xr.DataArray(np.array([[0.2, 0.4]]), dims=("y", "x"))
    ndbi = xr.DataArray(np.array([[0.6, 0.8]]), dims=("y", "x"))
    metrics_df = aggregate_city_metrics("taipei", ndvi, ndbi)
    
    # Join comparison and metrics
    joined = pd.merge(comparison_df, metrics_df, on="city")
    signature_df = build_city_signature_table(joined)
    assert "signature_score" in signature_df.columns
    
    # 2. Priority Zones
    lst = xr.DataArray(np.array([[38.0]]), dims=("y", "x"))
    ndvi_score = xr.DataArray(np.array([[0.1]]), dims=("y", "x"))
    ndbi_score = xr.DataArray(np.array([[0.9]]), dims=("y", "x"))
    
    score = priority_score(
        lst=lst,
        ndvi=ndvi_score,
        ndbi=ndbi_score,
        weights={"lst": 0.5, "green": 0.3, "built": 0.2}
    )
    score.attrs["crs"] = "EPSG:3857"
    score.coords["y"] = [2500000.0]
    score.coords["x"] = [1200000.0]
    score.attrs["x_resolution"] = 10.0
    score.attrs["y_resolution"] = 10.0
    
    priority_gdf = vectorize_priority_cells(score, threshold=0.0) # Will vectorise since score is high
    assert not priority_gdf.empty
    assert priority_gdf.crs == "EPSG:3857"
    
    # 3. Park Cooling
    park_samples = pd.DataFrame({
        "park_id": ["park-a"] * 8,
        "buffer_m": [0, 0, 0, 0, 100, 100, 100, 100],
        "lst_c": [30.0, 30.5, 31.0, 31.0, 33.0, 33.5, 34.0, 34.0],
    })
    park_cooling_df = pci_summary(park_samples, inner_buffer=0, outer_buffer=100, n_boot=250, seed=7)
    assert not park_cooling_df.empty
    assert "delta_lst_c" in park_cooling_df.columns
