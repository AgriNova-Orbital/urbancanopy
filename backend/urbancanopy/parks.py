import numpy as np
import pandas as pd


def pci_summary(
    samples: pd.DataFrame,
    *,
    inner_buffer: int,
    outer_buffer: int,
    n_boot: int,
    seed: int,
) -> pd.DataFrame:
    park = samples.loc[samples["buffer_m"] == inner_buffer, "lst_c"].to_numpy()
    ring = samples.loc[samples["buffer_m"] == outer_buffer, "lst_c"].to_numpy()
    delta = float(np.median(ring) - np.median(park))

    rng = np.random.default_rng(seed)
    boot = []
    for _ in range(n_boot):
        boot.append(
            float(
                np.median(rng.choice(ring, len(ring), replace=True))
                - np.median(rng.choice(park, len(park), replace=True))
            )
        )

    return pd.DataFrame(
        {
            "delta_lst_c": [delta],
            "ci_low_c": [float(np.percentile(boot, 2.5))],
            "ci_high_c": [float(np.percentile(boot, 97.5))],
        }
    )
