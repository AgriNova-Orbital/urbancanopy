from pathlib import Path

import geopandas as gpd
from shapely.geometry import Polygon

from urbancanopy.cities import (
    CITY_FIXTURES,
    build_comparison_zones,
    get_city_fixture_path,
)


def test_city_registry_exposes_supported_fixture_paths() -> None:
    assert set(CITY_FIXTURES) == {"taipei", "tokyo", "london", "new_york"}
    assert get_city_fixture_path("taipei").name == "taipei.geojson"


def test_get_city_fixture_path_defaults_to_runtime_city_data() -> None:
    path = get_city_fixture_path("taipei")

    assert path == (
        Path(__file__).resolve().parent.parent
        / "data"
        / "inputs"
        / "cities"
        / "taipei.geojson"
    )


def test_get_city_fixture_path_supports_base_path_override() -> None:
    path = get_city_fixture_path("tokyo", base_path="/tmp/custom-cities")

    assert str(path) == "/tmp/custom-cities/tokyo.geojson"


def test_get_city_fixture_path_rejects_unsupported_city() -> None:
    try:
        get_city_fixture_path("paris")
    except ValueError as exc:
        assert str(exc) == "Unsupported city: paris"
    else:
        raise AssertionError("expected ValueError for unsupported city")


def test_build_comparison_zones_returns_core_and_outer_ring() -> None:
    city = gpd.GeoDataFrame(
        {"city": ["taipei"]},
        geometry=[Polygon([(0, 0), (4, 0), (4, 4), (0, 4)])],
        crs="EPSG:3857",
    )

    zones = build_comparison_zones(city, inner_km=0, outer_km=5, exclude_core_to_km=1)

    assert set(zones["zone"]) == {"urban_core", "outer_ring"}
    assert zones.loc[zones["zone"] == "outer_ring", "geometry"].iloc[0].area > 0


def test_build_comparison_zones_projects_geographic_inputs_and_uses_inner_km() -> None:
    city = gpd.GeoDataFrame(
        {"city": ["taipei"]},
        geometry=[
            Polygon(
                [(121.50, 25.02), (121.54, 25.02), (121.54, 25.06), (121.50, 25.06)]
            )
        ],
        crs="EPSG:4326",
    )

    zones = build_comparison_zones(city, inner_km=1, outer_km=5, exclude_core_to_km=2)

    projected_crs = city.estimate_utm_crs()

    assert projected_crs is not None

    projected_city = city.to_crs(projected_crs)
    projected_zones = zones.to_crs(projected_crs)
    expected_outer = (
        projected_city.buffer(5000).difference(projected_city.buffer(2000)).iloc[0]
    )

    assert zones.crs == city.crs
    assert (
        projected_zones.loc[projected_zones["zone"] == "urban_core", "geometry"]
        .iloc[0]
        .area
        > projected_city.geometry.iloc[0].area
    )
    outer_area = (
        projected_zones.loc[projected_zones["zone"] == "outer_ring", "geometry"]
        .iloc[0]
        .area
    )
    assert abs(outer_area - expected_outer.area) / expected_outer.area < 0.01
