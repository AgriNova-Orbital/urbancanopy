import numpy as np
import xarray as xr

from urbancanopy.masking import apply_binary_mask, seasonal_median


def test_apply_binary_mask_sets_invalid_pixels_to_nan() -> None:
    data = xr.DataArray(np.array([[1.0, 2.0], [3.0, 4.0]]), dims=("y", "x"))
    valid = xr.DataArray(np.array([[1, 0], [1, 1]]), dims=("y", "x"))

    masked = apply_binary_mask(data, valid)

    assert float(masked.values[0, 0]) == 1.0
    assert np.isnan(masked.values[0, 1])


def test_apply_binary_mask_treats_nan_mask_values_as_invalid() -> None:
    data = xr.DataArray(np.array([[1.0, 2.0], [3.0, 4.0]]), dims=("y", "x"))
    valid = xr.DataArray(np.array([[1.0, np.nan], [1.0, 1.0]]), dims=("y", "x"))

    masked = apply_binary_mask(data, valid)

    assert np.isnan(masked.values[0, 1])


def test_seasonal_median_reduces_time_dimension() -> None:
    cube = xr.DataArray(
        np.array(
            [
                [[1.0, np.nan], [5.0, 7.0]],
                [[2.0, 4.0], [6.0, 8.0]],
            ]
        ),
        dims=("time", "y", "x"),
    )

    composite = seasonal_median(cube)

    assert composite.dims == ("y", "x")
    assert float(composite.values[0, 0]) == 1.5
    assert float(composite.values[0, 1]) == 4.0
