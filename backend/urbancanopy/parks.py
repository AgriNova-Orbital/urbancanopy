import zlib

import numpy as np
import pandas as pd


SUMMARY_COLUMNS = ["park_id", "delta_lst_c", "ci_low_c", "ci_high_c"]


def pci_summary(
    samples: pd.DataFrame,
    *,
    inner_buffer: int,
    outer_buffer: int,
    n_boot: int,
    seed: int,
) -> pd.DataFrame:
    if n_boot <= 0:
        msg = "n_boot must be greater than 0"
        raise ValueError(msg)

    if samples.empty:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)

    summaries: list[dict[str, float | str]] = []

    for park_id, park_samples in samples.groupby("park_id", sort=True):
        park = park_samples.loc[
            park_samples["buffer_m"] == inner_buffer, "lst_c"
        ].to_numpy()
        if len(park) == 0:
            msg = f"park '{park_id}' is missing samples for buffer {inner_buffer}"
            raise ValueError(msg)

        ring = park_samples.loc[
            park_samples["buffer_m"] == outer_buffer, "lst_c"
        ].to_numpy()
        if len(ring) == 0:
            msg = f"park '{park_id}' is missing samples for buffer {outer_buffer}"
            raise ValueError(msg)

        delta = float(np.median(ring) - np.median(park))
        park_seed = (int(seed) + zlib.crc32(str(park_id).encode("utf-8"))) % (2**32)
        rng = np.random.default_rng(park_seed)
        boot = []
        for _ in range(n_boot):
            boot.append(
                float(
                    np.median(rng.choice(ring, len(ring), replace=True))
                    - np.median(rng.choice(park, len(park), replace=True))
                )
            )
        summaries.append(
            {
                "park_id": str(park_id),
                "delta_lst_c": delta,
                "ci_low_c": float(np.percentile(boot, 2.5)),
                "ci_high_c": float(np.percentile(boot, 97.5)),
            }
        )

    return pd.DataFrame(summaries, columns=SUMMARY_COLUMNS)
