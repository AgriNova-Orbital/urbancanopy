import pandas as pd
import xarray as xr


def aggregate_city_metrics(city: str, ndvi: xr.DataArray, ndbi: xr.DataArray) -> pd.DataFrame:
    mean_ndvi = float(ndvi.mean(skipna=True))
    mean_ndbi = float(ndbi.mean(skipna=True))
    
    return pd.DataFrame({
        "city": [city],
        "mean_ndvi": [mean_ndvi],
        "mean_ndbi": [mean_ndbi]
    })
