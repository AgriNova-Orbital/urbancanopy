import xarray as xr


def normalize(data: xr.DataArray) -> xr.DataArray:
    span = data.max() - data.min()
    if float(span) == 0.0:
        return xr.zeros_like(data, dtype=float)
    return (data - data.min()) / span


def priority_score(
    *,
    lst: xr.DataArray,
    ndvi: xr.DataArray,
    ndbi: xr.DataArray,
    weights: dict[str, float],
) -> xr.DataArray:
    return (
        weights["lst"] * normalize(lst)
        + weights["green"] * (1 - normalize(ndvi))
        + weights["built"] * normalize(ndbi)
    )
