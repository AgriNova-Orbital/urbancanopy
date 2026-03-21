import geopandas as gpd
from shapely.geometry import Polygon

from urbancanopy.cities import build_comparison_zones


def test_build_comparison_zones_returns_core_and_outer_ring() -> None:
    city = gpd.GeoDataFrame(
        {"city": ["taipei"]},
        geometry=[Polygon([(0, 0), (4, 0), (4, 4), (0, 4)])],
        crs="EPSG:3857",
    )

    zones = build_comparison_zones(city, inner_km=0, outer_km=5, exclude_core_to_km=1)

    assert set(zones["zone"]) == {"urban_core", "outer_ring"}
    assert zones.loc[zones["zone"] == "outer_ring", "geometry"].iloc[0].area > 0
