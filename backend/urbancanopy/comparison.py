import pandas as pd


def summarize_city_heat_gap(samples: pd.DataFrame) -> pd.DataFrame:
    grouped = samples.groupby(["city", "zone"])["lst_c"].median().unstack()
    grouped["heat_gap_c"] = grouped["urban_core"] - grouped["outer_ring"]
    return grouped.reset_index()[["city", "heat_gap_c"]]
