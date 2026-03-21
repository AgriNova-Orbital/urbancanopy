import pandas as pd


def _normalize(series: pd.Series) -> pd.Series:
    return (series - series.min()) / (series.max() - series.min())


def build_city_signature_table(metrics: pd.DataFrame) -> pd.DataFrame:
    scored = metrics.copy()
    scored["signature_score"] = (
        0.5 * _normalize(scored["heat_gap_c"])
        + 0.3 * (1 - _normalize(scored["mean_ndvi"]))
        + 0.2 * _normalize(scored["mean_ndbi"])
    )
    return scored.sort_values("signature_score", ascending=False).reset_index(drop=True)
