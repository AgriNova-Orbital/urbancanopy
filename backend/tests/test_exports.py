import json
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from shapely.geometry import box
import geopandas as gpd

from urbancanopy.exports import export_priority_zones, export_city_comparison, export_city_signature, export_park_cooling

def test_export_priority_zones_produces_valid_geojson(tmp_path):
    gdf = gpd.GeoDataFrame({
        "priority_score": [0.9],
        "geometry": [box(0, 0, 1, 1)]
    }, crs="EPSG:4326")
    
    out_path = tmp_path / "priority_zones.geojson"
    export_priority_zones(gdf, out_path)
    
    assert out_path.exists()
    
    with open(out_path) as f:
        data = json.load(f)
        
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 1
    assert data["features"][0]["properties"]["priority_score"] == 0.9

def test_export_city_comparison_produces_valid_csv(tmp_path):
    df = pd.DataFrame({
        "city": ["taipei"],
        "heat_gap_c": [2.5]
    })
    
    out_path = tmp_path / "city_comparison.csv"
    export_city_comparison(df, out_path)
    
    assert out_path.exists()
    saved = pd.read_csv(out_path)
    assert saved.loc[0, "city"] == "taipei"
    assert saved.loc[0, "heat_gap_c"] == 2.5

def test_export_city_signature_produces_valid_csv(tmp_path):
    df = pd.DataFrame({
        "city": ["taipei"],
        "heat_gap_c": [2.5],
        "mean_ndvi": [0.3],
        "mean_ndbi": [0.7],
        "signature_score": [0.8]
    })
    
    out_path = tmp_path / "city_signature.csv"
    export_city_signature(df, out_path)
    
    assert out_path.exists()
    saved = pd.read_csv(out_path)
    assert saved.loc[0, "city"] == "taipei"
    assert saved.loc[0, "signature_score"] == 0.8

def test_export_park_cooling_produces_valid_csv(tmp_path):
    df = pd.DataFrame({
        "park_id": ["park-a"],
        "delta_lst_c": [2.5],
        "ci_low_c": [1.5],
        "ci_high_c": [3.5]
    })
    
    out_path = tmp_path / "park_cooling.csv"
    export_park_cooling(df, out_path)
    
    assert out_path.exists()
    saved = pd.read_csv(out_path)
    assert saved.loc[0, "park_id"] == "park-a"
    assert saved.loc[0, "delta_lst_c"] == 2.5
