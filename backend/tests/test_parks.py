import pandas as pd

from urbancanopy.parks import pci_summary


def test_pci_summary_returns_delta_and_bootstrap_interval() -> None:
    samples = pd.DataFrame(
        {
            "park_id": ["park-a"] * 8,
            "buffer_m": [0, 0, 0, 0, 100, 100, 100, 100],
            "lst_c": [30.0, 30.5, 31.0, 31.0, 33.0, 33.5, 34.0, 34.0],
        }
    )

    summary = pci_summary(samples, inner_buffer=0, outer_buffer=100, n_boot=250, seed=7)

    assert summary.loc[0, "delta_lst_c"] > 2.0
    assert (
        summary.loc[0, "ci_low_c"]
        < summary.loc[0, "delta_lst_c"]
        < summary.loc[0, "ci_high_c"]
    )
