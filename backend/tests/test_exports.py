import json
import pandas as pd
import pytest
from shapely.geometry import box
import geopandas as gpd

from urbancanopy.exports import (
    export_priority_zones,
    export_city_comparison,
    export_city_signature,
    export_park_cooling,
)


def test_export_priority_zones_produces_valid_geojson(tmp_path):
    gdf = gpd.GeoDataFrame(
        {"priority_score": [0.9], "geometry": [box(0, 0, 1, 1)]}, crs="EPSG:4326"
    )

    out_path = tmp_path / "priority_zones.geojson"
    export_priority_zones(gdf, out_path)

    assert out_path.exists()

    with open(out_path) as f:
        data = json.load(f)

    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 1
    assert data["features"][0]["properties"]["priority_score"] == 0.9
    assert data["features"][0]["properties"]["zone_id"] == "zone-1"


def test_export_priority_zones_reprojects_to_epsg_4326(tmp_path):
    gdf = gpd.GeoDataFrame(
        {
            "priority_score": [0.9],
            "geometry": [box(12100000, 2500000, 12101000, 2501000)],
        },
        crs="EPSG:3857",
    )

    out_path = tmp_path / "priority_zones.geojson"

    export_priority_zones(gdf, out_path)

    saved = gpd.read_file(out_path)

    assert saved.crs == "EPSG:4326"
    assert saved.loc[0, "zone_id"] == "zone-1"
    minx, miny, maxx, maxy = saved.geometry.iloc[0].bounds
    assert -180 <= minx <= 180
    assert -90 <= miny <= 90
    assert -180 <= maxx <= 180
    assert -90 <= maxy <= 90


@pytest.mark.parametrize(
    ("exporter", "data", "expected_message"),
    [
        (
            export_priority_zones,
            gpd.GeoDataFrame({"geometry": [box(0, 0, 1, 1)]}, crs="EPSG:4326"),
            "priority_score",
        ),
        (
            export_city_comparison,
            pd.DataFrame({"city": ["taipei"]}),
            "heat_gap_c",
        ),
        (
            export_city_signature,
            pd.DataFrame(
                {
                    "city": ["taipei"],
                    "heat_gap_c": [2.5],
                    "mean_ndvi": [0.3],
                    "mean_ndbi": [0.7],
                }
            ),
            "signature_score",
        ),
        (
            export_park_cooling,
            pd.DataFrame(
                {
                    "park_id": ["park-a"],
                    "delta_lst_c": [2.5],
                    "ci_low_c": [1.5],
                }
            ),
            "ci_high_c",
        ),
    ],
)
def test_export_contracts_require_expected_columns(
    tmp_path, exporter, data, expected_message
):
    out_path = tmp_path / "out"

    with pytest.raises(ValueError, match=expected_message):
        exporter(data, out_path)


def test_export_city_comparison_produces_valid_csv(tmp_path):
    df = pd.DataFrame({"city": ["taipei"], "heat_gap_c": [2.5]})

    out_path = tmp_path / "city_comparison.csv"
    export_city_comparison(df, out_path)

    assert out_path.exists()
    saved = pd.read_csv(out_path)
    assert saved.loc[0, "city"] == "taipei"
    assert saved.loc[0, "heat_gap_c"] == 2.5


def test_export_city_signature_produces_valid_csv(tmp_path):
    df = pd.DataFrame(
        {
            "city": ["taipei"],
            "heat_gap_c": [2.5],
            "mean_ndvi": [0.3],
            "mean_ndbi": [0.7],
            "signature_score": [0.8],
        }
    )

    out_path = tmp_path / "city_signature.csv"
    export_city_signature(df, out_path)

    assert out_path.exists()
    saved = pd.read_csv(out_path)
    assert saved.loc[0, "city"] == "taipei"
    assert saved.loc[0, "signature_score"] == 0.8


def test_export_park_cooling_produces_valid_csv(tmp_path):
    df = pd.DataFrame(
        {
            "park_id": ["park-a"],
            "delta_lst_c": [2.5],
            "ci_low_c": [1.5],
            "ci_high_c": [3.5],
        }
    )

    out_path = tmp_path / "park_cooling.csv"
    export_park_cooling(df, out_path)

    assert out_path.exists()
    saved = pd.read_csv(out_path)
    assert saved.loc[0, "park_id"] == "park-a"
    assert saved.loc[0, "delta_lst_c"] == 2.5
