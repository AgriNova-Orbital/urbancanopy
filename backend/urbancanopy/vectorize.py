import geopandas as gpd
import xarray as xr
from shapely.geometry import box


def vectorize_priority_cells(
    score: xr.DataArray, *, threshold: float = 0.5, min_area: float = 0.0
) -> gpd.GeoDataFrame:
    rows: list[dict[str, object]] = []

    for y_index in range(score.sizes["y"]):
        for x_index in range(score.sizes["x"]):
            value = float(score.values[y_index, x_index])
            if value < threshold:
                continue

            geometry = box(x_index, y_index, x_index + 1, y_index + 1)
            if geometry.area < min_area:
                continue

            rows.append({"priority_score": value, "geometry": geometry})

    return gpd.GeoDataFrame(rows, columns=["priority_score", "geometry"])
