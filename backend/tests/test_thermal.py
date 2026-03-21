import numpy as np
import pytest
import xarray as xr

from urbancanopy.thermal import hotspot_mask


def test_hotspot_mask_marks_top_percentile_pixels() -> None:
    lst = xr.DataArray(np.array([[28.0, 31.0], [34.0, 36.0]]), dims=("y", "x"))

    mask = hotspot_mask(lst, percentile=75)

    assert mask.values.tolist() == [[False, False], [False, True]]


def test_hotspot_mask_ignores_nan_pixels_for_percentile_selection() -> None:
    lst = xr.DataArray(np.array([[28.0, np.nan], [34.0, 36.0]]), dims=("y", "x"))

    mask = hotspot_mask(lst, percentile=75)

    assert mask.values.tolist() == [[False, False], [False, True]]


def test_hotspot_mask_rejects_out_of_range_percentiles() -> None:
    lst = xr.DataArray(np.array([[28.0, 31.0], [34.0, 36.0]]), dims=("y", "x"))

    with pytest.raises(ValueError, match="percentile must be between 0 and 100"):
        hotspot_mask(lst, percentile=101)
