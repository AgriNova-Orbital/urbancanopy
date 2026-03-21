import xarray as xr


def compute_ndvi(*, nir: xr.DataArray, red: xr.DataArray) -> xr.DataArray:
    return (nir - red) / (nir + red)


def compute_ndbi(*, swir: xr.DataArray, nir: xr.DataArray) -> xr.DataArray:
    return (swir - nir) / (swir + nir)


def compute_evi(
    *, nir: xr.DataArray, red: xr.DataArray, blue: xr.DataArray
) -> xr.DataArray:
    return 2.5 * (nir - red) / (nir + (6 * red) - (7.5 * blue) + 1)
