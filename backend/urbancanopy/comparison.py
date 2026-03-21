import pandas as pd


def _require_columns(table: pd.DataFrame, required: set[str], table_name: str) -> None:
    missing = sorted(required.difference(table.columns))
    if missing:
        names = ", ".join(missing)
        raise ValueError(f"{table_name} missing required columns: {names}")


def _build_city_surface_metrics(surface_context: pd.DataFrame) -> pd.DataFrame:
    aggregated_columns = {"city", "mean_ndvi", "mean_ndbi"}
    sample_columns = {"city", "ndvi", "ndbi"}

    if aggregated_columns.issubset(surface_context.columns):
        city_surface_metrics = surface_context.loc[
            :, ["city", "mean_ndvi", "mean_ndbi"]
        ].copy()
        return (
            city_surface_metrics.groupby("city", as_index=False)
            .agg({"mean_ndvi": "mean", "mean_ndbi": "mean"})
            .reset_index(drop=True)
        )

    if sample_columns.issubset(surface_context.columns):
        return (
            surface_context.groupby("city", as_index=False)
            .agg(mean_ndvi=("ndvi", "mean"), mean_ndbi=("ndbi", "mean"))
            .reset_index(drop=True)
        )

    raise ValueError(
        "surface context missing required columns: "
        "expected city with mean_ndvi/mean_ndbi or ndvi/ndbi"
    )


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


def build_modeling_ready_city_metrics(
    heat_gap_summary: pd.DataFrame, surface_context: pd.DataFrame
) -> pd.DataFrame:
    _require_columns(heat_gap_summary, {"city", "heat_gap_c"}, "city heat-gap summary")

    city_surface_metrics = _build_city_surface_metrics(surface_context)
    merged = heat_gap_summary.loc[:, ["city", "heat_gap_c"]].merge(
        city_surface_metrics,
        on="city",
        how="left",
        indicator=True,
    )

    metrics_missing_mask = (
        (merged["_merge"] == "left_only")
        | merged["mean_ndvi"].isna()
        | merged["mean_ndbi"].isna()
    )
    missing_cities = merged.loc[metrics_missing_mask, "city"]
    if not missing_cities.empty:
        cities = ", ".join(str(city) for city in missing_cities)
        raise ValueError(f"missing city metrics for cities: {cities}")

    return merged.loc[:, ["city", "heat_gap_c", "mean_ndvi", "mean_ndbi"]]
