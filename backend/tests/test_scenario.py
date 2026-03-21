import numpy as np
import xarray as xr

from urbancanopy.scenario import apply_canopy_scenario


def test_apply_canopy_scenario_returns_low_mid_high_temperature_bands() -> None:
    lst = xr.DataArray(np.array([[35.0]]), dims=("y", "x"))

    bands = apply_canopy_scenario(lst=lst, canopy_delta_pct=10)

    assert float(bands["low"].values[0, 0]) == 34.9
    assert float(bands["mid"].values[0, 0]) == 34.4
    assert float(bands["high"].values[0, 0]) == 32.7
