import numpy as np
import xarray as xr

from urbancanopy.indices import compute_evi, compute_ndbi, compute_ndvi


def test_compute_ndvi_matches_expected_ratio() -> None:
    nir = xr.DataArray(np.array([[0.8, 0.6]]), dims=("y", "x"))
    red = xr.DataArray(np.array([[0.2, 0.3]]), dims=("y", "x"))

    ndvi = compute_ndvi(nir=nir, red=red)

    assert np.allclose(ndvi.values, [[0.6, 0.33333333]])


def test_compute_ndbi_matches_expected_ratio() -> None:
    swir = xr.DataArray(np.array([[0.7, 0.5]]), dims=("y", "x"))
    nir = xr.DataArray(np.array([[0.3, 0.4]]), dims=("y", "x"))

    ndbi = compute_ndbi(swir=swir, nir=nir)

    assert np.allclose(ndbi.values, [[0.4, 0.11111111]])


def test_compute_evi_matches_expected_ratio() -> None:
    nir = xr.DataArray(np.array([[0.8, 0.7]]), dims=("y", "x"))
    red = xr.DataArray(np.array([[0.2, 0.3]]), dims=("y", "x"))
    blue = xr.DataArray(np.array([[0.1, 0.1]]), dims=("y", "x"))

    evi = compute_evi(nir=nir, red=red, blue=blue)

    assert np.allclose(evi.values, [[0.66666667, 0.36363636]])
