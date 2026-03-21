import numpy as np
import xarray as xr

from urbancanopy.thermal import hotspot_mask


def test_hotspot_mask_marks_top_percentile_pixels() -> None:
    lst = xr.DataArray(np.array([[28.0, 31.0], [34.0, 36.0]]), dims=("y", "x"))

    mask = hotspot_mask(lst, percentile=75)

    assert mask.values.tolist() == [[False, False], [False, True]]
