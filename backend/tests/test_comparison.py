import pandas as pd
import pytest

from urbancanopy.comparison import (
    build_modeling_ready_city_metrics,
    summarize_city_heat_gap,
)
from urbancanopy.modeling import build_city_signature_table


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
    assert summary.loc[0, "heat_gap_c"] == pytest.approx(2.8)


def test_summarize_city_heat_gap_requires_both_comparison_zones() -> None:
    samples = pd.DataFrame(
        {
            "city": ["taipei"] * 3,
            "zone": ["urban_core", "urban_core", "urban_core"],
            "lst_c": [34.0, 34.2, 33.8],
        }
    )

    with pytest.raises(ValueError, match="missing required zones"):
        summarize_city_heat_gap(samples)


def test_build_modeling_ready_city_metrics_produces_modeling_schema() -> None:
    heat_gap_summary = pd.DataFrame(
        {
            "city": ["taipei", "tokyo"],
            "heat_gap_c": [2.8, 1.5],
        }
    )
    surface_samples = pd.DataFrame(
        {
            "city": ["taipei", "taipei", "tokyo", "tokyo"],
            "ndvi": [0.2, 0.4, 0.5, 0.7],
            "ndbi": [0.7, 0.5, 0.3, 0.1],
        }
    )

    metrics = build_modeling_ready_city_metrics(heat_gap_summary, surface_samples)

    assert list(metrics.columns) == ["city", "heat_gap_c", "mean_ndvi", "mean_ndbi"]
    assert metrics.to_dict("records") == [
        {
            "city": "taipei",
            "heat_gap_c": 2.8,
            "mean_ndvi": pytest.approx(0.3),
            "mean_ndbi": pytest.approx(0.6),
        },
        {
            "city": "tokyo",
            "heat_gap_c": 1.5,
            "mean_ndvi": pytest.approx(0.6),
            "mean_ndbi": pytest.approx(0.2),
        },
    ]


def test_build_modeling_ready_city_metrics_outputs_table_modeling_can_score() -> None:
    heat_gap_summary = pd.DataFrame(
        {
            "city": ["taipei", "tokyo"],
            "heat_gap_c": [3.0, 1.0],
        }
    )
    city_surface_context = pd.DataFrame(
        {
            "city": ["taipei", "tokyo"],
            "mean_ndvi": [0.2, 0.5],
            "mean_ndbi": [0.8, 0.4],
        }
    )

    metrics = build_modeling_ready_city_metrics(heat_gap_summary, city_surface_context)

    table = build_city_signature_table(metrics)

    assert list(table.columns) == [
        "city",
        "heat_gap_c",
        "mean_ndvi",
        "mean_ndbi",
        "signature_score",
    ]
    assert table.loc[0, "city"] == "taipei"


def test_build_modeling_ready_city_metrics_requires_metrics_for_each_heat_gap_city() -> (
    None
):
    heat_gap_summary = pd.DataFrame(
        {
            "city": ["taipei", "tokyo"],
            "heat_gap_c": [2.8, 1.5],
        }
    )
    city_surface_context = pd.DataFrame(
        {
            "city": ["taipei"],
            "mean_ndvi": [0.3],
            "mean_ndbi": [0.6],
        }
    )

    with pytest.raises(ValueError, match="missing city metrics for cities: tokyo"):
        build_modeling_ready_city_metrics(heat_gap_summary, city_surface_context)
