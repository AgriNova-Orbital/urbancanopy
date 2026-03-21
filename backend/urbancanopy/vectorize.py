import math

import geopandas as gpd
import numpy as np
import xarray as xr
from shapely.geometry import box


def _get_cell_edges(score: xr.DataArray, axis: str, resolution_attr: str) -> np.ndarray:
    if axis not in score.coords:
        raise ValueError(f"score must define an '{axis}' coordinate")

    coordinates = np.asarray(score.coords[axis].values, dtype=float)
    if coordinates.ndim != 1:
        raise ValueError(f"score coordinate '{axis}' must be one-dimensional")

    if len(coordinates) == 1:
        resolution = score.attrs.get(resolution_attr)
        if resolution is None:
            raise ValueError(
                f"score.attrs['{resolution_attr}'] must be present when score has a single '{axis}' coordinate"
            )

        half_resolution = abs(float(resolution)) / 2.0
        center = coordinates[0]
        return np.array([center - half_resolution, center + half_resolution])

    midpoints = (coordinates[:-1] + coordinates[1:]) / 2.0
    first_edge = coordinates[0] - (midpoints[0] - coordinates[0])
    last_edge = coordinates[-1] + (coordinates[-1] - midpoints[-1])

    return np.concatenate(([first_edge], midpoints, [last_edge]))


def vectorize_priority_cells(
    score: xr.DataArray, *, threshold: float = 0.5, min_area: float = 0.0
) -> gpd.GeoDataFrame:
    crs = score.attrs.get("crs")
    if crs is None:
        raise ValueError("score.attrs['crs'] must be present")

    x_edges = _get_cell_edges(score, "x", "x_resolution")
    y_edges = _get_cell_edges(score, "y", "y_resolution")
    rows: list[dict[str, object]] = []

    for y_index in range(score.sizes["y"]):
        for x_index in range(score.sizes["x"]):
            value = float(score.values[y_index, x_index])
            if math.isnan(value):
                continue
            if value < threshold:
                continue

            geometry = box(
                min(x_edges[x_index], x_edges[x_index + 1]),
                min(y_edges[y_index], y_edges[y_index + 1]),
                max(x_edges[x_index], x_edges[x_index + 1]),
                max(y_edges[y_index], y_edges[y_index + 1]),
            )
            if geometry.area < min_area:
                continue

            rows.append({"priority_score": value, "geometry": geometry})

    return gpd.GeoDataFrame(rows, columns=["priority_score", "geometry"], crs=crs)
