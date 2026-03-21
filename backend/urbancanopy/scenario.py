import xarray as xr

COEFFICIENTS = {"low": 0.01, "mid": 0.06, "high": 0.23}

def apply_canopy_scenario(*, lst: xr.DataArray, canopy_delta_pct: float) -> dict[str, xr.DataArray]:
    return {
        label: lst - (beta * canopy_delta_pct)
        for label, beta in COEFFICIENTS.items()
    }
