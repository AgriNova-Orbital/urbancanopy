import numpy as np
import pytest
import xarray as xr

from urbancanopy.vectorize import vectorize_priority_cells


def test_vectorize_priority_cells_returns_polygons_for_high_score_pixels() -> None:
    score = xr.DataArray(
        np.array([[0.2, 0.9], [0.8, 0.1]]),
        dims=("y", "x"),
        coords={"y": [200.0, 190.0], "x": [100.0, 110.0]},
        attrs={"crs": "EPSG:3857"},
    )

    zones = vectorize_priority_cells(score, threshold=0.75)

    assert len(zones) == 2
    assert set(zones["priority_score"].round(1)) == {0.8, 0.9}


def test_vectorize_priority_cells_returns_georeferenced_polygons_with_score_crs() -> (
    None
):
    score = xr.DataArray(
        np.array([[0.1, 0.9], [0.8, 0.2]]),
        dims=("y", "x"),
        coords={"y": [200.0, 190.0], "x": [100.0, 110.0]},
        attrs={"crs": "EPSG:3857"},
    )

    zones = vectorize_priority_cells(score, threshold=0.75)

    assert zones.crs == "EPSG:3857"
    assert len(zones) == 2
    bounds = {
        round(float(score_value), 1): tuple(
            round(value, 6) for value in geometry.bounds
        )
        for score_value, geometry in zip(
            zones["priority_score"], zones.geometry, strict=True
        )
    }
    assert bounds[0.9] == (105.0, 195.0, 115.0, 205.0)
    assert bounds[0.8] == (95.0, 185.0, 105.0, 195.0)


def test_vectorize_priority_cells_requires_crs_metadata() -> None:
    score = xr.DataArray(
        np.array([[0.9]]),
        dims=("y", "x"),
        coords={"y": [200.0], "x": [100.0]},
        attrs={"x_resolution": 10.0, "y_resolution": 20.0},
    )

    with pytest.raises(ValueError, match=r"score.attrs\['crs'\] must be present"):
        vectorize_priority_cells(score, threshold=0.5)


def test_vectorize_priority_cells_filters_small_georeferenced_polygons_by_area() -> (
    None
):
    score = xr.DataArray(
        np.array([[0.9]]),
        dims=("y", "x"),
        coords={"y": [200.0], "x": [100.0]},
        attrs={"crs": "EPSG:3857", "x_resolution": 10.0, "y_resolution": 20.0},
    )

    zones = vectorize_priority_cells(score, threshold=0.5, min_area=2.0)

    assert len(zones) == 1

    zones = vectorize_priority_cells(score, threshold=0.5, min_area=201.0)

    assert zones.empty


def test_vectorize_priority_cells_skips_nan_score_cells() -> None:
    score = xr.DataArray(
        np.array([[np.nan, 0.9]]),
        dims=("y", "x"),
        coords={"y": [200.0], "x": [100.0, 110.0]},
        attrs={"crs": "EPSG:3857", "y_resolution": 10.0},
    )

    zones = vectorize_priority_cells(score, threshold=0.5)

    assert len(zones) == 1
    assert set(zones["priority_score"].round(1)) == {0.9}
