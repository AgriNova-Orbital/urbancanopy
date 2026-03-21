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


def test_build_comparison_zones_returns_core_and_outer_ring() -> None:
    city = gpd.GeoDataFrame(
        {"city": ["taipei"]},
        geometry=[Polygon([(0, 0), (4, 0), (4, 4), (0, 4)])],
        crs="EPSG:3857",
    )

    zones = build_comparison_zones(city, inner_km=0, outer_km=5, exclude_core_to_km=1)

    assert set(zones["zone"]) == {"urban_core", "outer_ring"}
    assert zones.loc[zones["zone"] == "outer_ring", "geometry"].iloc[0].area > 0
