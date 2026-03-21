import numpy as np
import xarray as xr


def hotspot_mask(lst: xr.DataArray, percentile: int) -> xr.DataArray:
    threshold = float(np.nanpercentile(lst.values, percentile))
    return lst >= threshold
