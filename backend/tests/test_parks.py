import pandas as pd
import pytest

from urbancanopy.parks import pci_summary


def test_pci_summary_returns_park_level_delta_and_bootstrap_interval() -> None:
    samples = pd.DataFrame(
        {
            "park_id": ["park-a"] * 8 + ["park-b"] * 8,
            "buffer_m": [0, 0, 0, 0, 100, 100, 100, 100] * 2,
            "lst_c": [
                30.0,
                30.5,
                31.0,
                31.0,
                33.0,
                33.5,
                34.0,
                34.0,
                27.5,
                28.0,
                28.0,
                28.5,
                29.0,
                29.0,
                29.5,
                30.0,
            ],
        }
    )

    summary = pci_summary(samples, inner_buffer=0, outer_buffer=100, n_boot=250, seed=7)

    assert list(summary.columns) == ["park_id", "delta_lst_c", "ci_low_c", "ci_high_c"]
    assert list(summary["park_id"]) == ["park-a", "park-b"]
    assert list(summary["delta_lst_c"].round(2)) == [3.0, 1.25]
    assert all(summary["ci_low_c"] < summary["delta_lst_c"])
    assert all(summary["delta_lst_c"] < summary["ci_high_c"])


def test_pci_summary_raises_for_missing_buffer_samples() -> None:
    samples = pd.DataFrame(
        {
            "park_id": ["park-a", "park-a", "park-b", "park-b"],
            "buffer_m": [0, 100, 0, 0],
            "lst_c": [30.0, 32.0, 29.0, 29.5],
        }
    )

    with pytest.raises(
        ValueError, match="park 'park-b' is missing samples for buffer 100"
    ):
        pci_summary(samples, inner_buffer=0, outer_buffer=100, n_boot=100, seed=7)


def test_pci_summary_raises_for_non_positive_bootstrap_count() -> None:
    samples = pd.DataFrame(
        {
            "park_id": ["park-a", "park-a"],
            "buffer_m": [0, 100],
            "lst_c": [30.0, 32.0],
        }
    )

    with pytest.raises(ValueError, match="n_boot must be greater than 0"):
        pci_summary(samples, inner_buffer=0, outer_buffer=100, n_boot=0, seed=7)
