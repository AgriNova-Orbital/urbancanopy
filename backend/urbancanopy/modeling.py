from typing import cast

import pandas as pd
from pandas import Series


def _normalize(series: Series) -> Series:
    span = series.max() - series.min()
    if span == 0:
        return Series(0.0, index=series.index)
    return (series - series.min()) / span


def build_city_signature_table(metrics: pd.DataFrame) -> pd.DataFrame:
    scored = metrics.copy()
    heat_gap = cast(Series, scored["heat_gap_c"])
    mean_ndvi = cast(Series, scored["mean_ndvi"])
    mean_ndbi = cast(Series, scored["mean_ndbi"])
    scored["signature_score"] = (
        0.5 * _normalize(heat_gap)
        + 0.3 * (1 - _normalize(mean_ndvi))
        + 0.2 * _normalize(mean_ndbi)
    )
    return scored.sort_values("signature_score", ascending=False).reset_index(drop=True)
