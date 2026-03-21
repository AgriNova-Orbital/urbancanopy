import xarray as xr


def apply_binary_mask(data: xr.DataArray, valid_mask: xr.DataArray) -> xr.DataArray:
    return data.where(valid_mask.astype(bool))


def seasonal_median(data: xr.DataArray) -> xr.DataArray:
    return data.median(dim="time", skipna=True)
