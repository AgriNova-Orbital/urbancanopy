import numpy as np
import xarray as xr

from urbancanopy.vectorize import vectorize_priority_cells


def test_vectorize_priority_cells_returns_polygons_for_high_score_pixels() -> None:
    score = xr.DataArray(np.array([[0.2, 0.9], [0.8, 0.1]]), dims=("y", "x"))

    zones = vectorize_priority_cells(score, threshold=0.75)

    assert len(zones) == 2
    assert set(zones["priority_score"].round(1)) == {0.8, 0.9}


def test_vectorize_priority_cells_filters_small_polygons_by_area() -> None:
    score = xr.DataArray(np.array([[0.9]]), dims=("y", "x"))

    zones = vectorize_priority_cells(score, threshold=0.5, min_area=2.0)

    assert zones.empty


def test_vectorize_priority_cells_skips_nan_score_cells() -> None:
    score = xr.DataArray(np.array([[np.nan, 0.9]]), dims=("y", "x"))

    zones = vectorize_priority_cells(score, threshold=0.5)

    assert len(zones) == 1
    assert set(zones["priority_score"].round(1)) == {0.9}
