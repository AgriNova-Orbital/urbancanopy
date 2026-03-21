import xarray as xr


def hotspot_mask(lst: xr.DataArray, percentile: int) -> xr.DataArray:
    if not 0 <= percentile <= 100:
        raise ValueError("percentile must be between 0 and 100")

    threshold = lst.quantile(percentile / 100, skipna=True)
    return lst >= threshold
