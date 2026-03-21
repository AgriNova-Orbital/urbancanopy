import numpy as np
import pytest
import xarray as xr
from pandas.testing import assert_frame_equal
import pandas as pd

from urbancanopy.aggregation import aggregate_city_metrics

def test_aggregate_city_metrics_computes_mean_indices() -> None:
    ndvi = xr.DataArray(np.array([[0.2, 0.4]]), dims=("y", "x"))
    ndbi = xr.DataArray(np.array([[0.6, 0.8]]), dims=("y", "x"))
    
    metrics = aggregate_city_metrics("taipei", ndvi, ndbi)
    
    assert metrics.loc[0, "city"] == "taipei"
    assert metrics.loc[0, "mean_ndvi"] == pytest.approx(0.3)
    assert metrics.loc[0, "mean_ndbi"] == pytest.approx(0.7)

def test_aggregate_city_metrics_ignores_nans() -> None:
    ndvi = xr.DataArray(np.array([[0.2, np.nan]]), dims=("y", "x"))
    ndbi = xr.DataArray(np.array([[np.nan, 0.8]]), dims=("y", "x"))
    
    metrics = aggregate_city_metrics("tokyo", ndvi, ndbi)
    
    assert metrics.loc[0, "city"] == "tokyo"
    assert metrics.loc[0, "mean_ndvi"] == pytest.approx(0.2)
    assert metrics.loc[0, "mean_ndbi"] == pytest.approx(0.8)

def test_aggregate_city_metrics_returns_nan_for_empty_arrays() -> None:
    ndvi = xr.DataArray(np.array([[np.nan, np.nan]]), dims=("y", "x"))
    ndbi = xr.DataArray(np.array([[np.nan, np.nan]]), dims=("y", "x"))
    
    metrics = aggregate_city_metrics("london", ndvi, ndbi)
    
    assert metrics.loc[0, "city"] == "london"
    assert pd.isna(metrics.loc[0, "mean_ndvi"])
    assert pd.isna(metrics.loc[0, "mean_ndbi"])
