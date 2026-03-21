import pandas as pd

from urbancanopy.comparison import summarize_city_heat_gap


def test_summarize_city_heat_gap_computes_core_minus_outer_delta() -> None:
    samples = pd.DataFrame(
        {
            "city": ["taipei"] * 6,
            "zone": [
                "urban_core",
                "urban_core",
                "urban_core",
                "outer_ring",
                "outer_ring",
                "outer_ring",
            ],
            "lst_c": [34.0, 34.2, 33.8, 31.0, 31.4, 31.2],
        }
    )

    summary = summarize_city_heat_gap(samples)

    assert summary.loc[0, "city"] == "taipei"
    assert summary.loc[0, "heat_gap_c"] > 2.5
