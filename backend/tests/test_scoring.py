import numpy as np
import xarray as xr

from urbancanopy.scoring import priority_score


def test_priority_score_combines_heat_green_and_built_layers() -> None:
    lst = xr.DataArray(np.array([[30.0, 40.0]]), dims=("y", "x"))
    ndvi = xr.DataArray(np.array([[0.8, 0.1]]), dims=("y", "x"))
    ndbi = xr.DataArray(np.array([[0.2, 0.9]]), dims=("y", "x"))

    score = priority_score(
        lst=lst,
        ndvi=ndvi,
        ndbi=ndbi,
        weights={"lst": 0.5, "green": 0.3, "built": 0.2},
    )

    assert score.values[0, 1] > score.values[0, 0]
