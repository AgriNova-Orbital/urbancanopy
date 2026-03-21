import pandas as pd

from urbancanopy.modeling import build_city_signature_table


def test_build_city_signature_table_ranks_hot_low_green_cities_higher() -> None:
    metrics = pd.DataFrame(
        {
            "city": ["taipei", "tokyo"],
            "heat_gap_c": [3.0, 1.0],
            "mean_ndvi": [0.2, 0.5],
            "mean_ndbi": [0.8, 0.4],
        }
    )

    table = build_city_signature_table(metrics)

    assert (
        table.loc[table["city"] == "taipei", "signature_score"].iloc[0]
        > table.loc[table["city"] == "tokyo", "signature_score"].iloc[0]
    )


def test_build_city_signature_table_keeps_signature_score_finite_for_constant_metric() -> (
    None
):
    metrics = pd.DataFrame(
        {
            "city": ["taipei", "tokyo"],
            "heat_gap_c": [2.0, 2.0],
            "mean_ndvi": [0.2, 0.5],
            "mean_ndbi": [0.8, 0.4],
        }
    )

    table = build_city_signature_table(metrics)

    assert bool(table["signature_score"].notna().all())
