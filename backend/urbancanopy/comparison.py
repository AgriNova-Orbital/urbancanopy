import pandas as pd


def summarize_city_heat_gap(samples: pd.DataFrame) -> pd.DataFrame:
    grouped = pd.DataFrame(
        samples.groupby(["city", "zone"])["lst_c"].median().unstack()
    )

    for zone in ("urban_core", "outer_ring"):
        if zone not in grouped:
            grouped[zone] = pd.NA

    grouped = grouped[["urban_core", "outer_ring"]]

    missing_mask = grouped.isna().any(axis=1)
    missing = [
        str(city) for city, is_missing in zip(grouped.index, missing_mask) if is_missing
    ]
    if missing:
        cities = ", ".join(missing)
        raise ValueError(f"missing required zones for cities: {cities}")

    grouped["heat_gap_c"] = grouped["urban_core"] - grouped["outer_ring"]
    return pd.DataFrame(
        {
            "city": [str(city) for city in grouped.index],
            "heat_gap_c": list(grouped["heat_gap_c"]),
        }
    )
