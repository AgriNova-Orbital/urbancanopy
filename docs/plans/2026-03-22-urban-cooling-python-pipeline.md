# Urban Cooling Python Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python-first geospatial pipeline that ingests open EO data, computes summer surface-heat and greening layers, ranks planting priority zones, and exports reproducible GeoJSON/CSV artifacts for later UI integration.

**Architecture:** Keep the backend as a small Python package under `backend/urbancanopy/` with thin modules for config, STAC access, raster processing, scoring, evidence analysis, scenarios, and exports. Use unit tests with synthetic xarray/geopandas fixtures for nearly all logic, and keep live EO access behind injectable interfaces so the pipeline remains testable and fast. The first deliverable is a CLI plus files in `backend/data/outputs/`; do not contort the analytics to match the current placeholder frontend schema yet.

**Tech Stack:** Python 3.11, `pytest`, `pystac-client`, `odc-stac`, `xarray`, `rioxarray`, `geopandas`, `rasterio`, `numpy`, `pandas`, `shapely`, `pyyaml`, `matplotlib`

---

### Task 1: Bootstrap the backend package and typed run configuration

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/urbancanopy/__init__.py`
- Create: `backend/urbancanopy/config.py`
- Create: `backend/tests/test_config.py`
- Create: `backend/configs/taipei-demo.yml`
- Create: `backend/data/inputs/.gitkeep`
- Create: `backend/data/outputs/.gitkeep`

**Step 1: Write the failing test**

```python
from pathlib import Path

from urbancanopy.config import load_run_config


def test_load_run_config_from_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "run.yml"
    config_path.write_text(
        """
name: taipei-demo
aoi_path: data/inputs/taipei_aoi.geojson
start_date: 2025-06-01
end_date: 2025-08-31
hotspot_percentile: 90
weights:
  lst: 0.5
  green: 0.3
  built: 0.2
buffer_distances_m: [0, 100, 300, 500]
scenario_canopy_delta_pct: 10
""".strip()
    )

    cfg = load_run_config(config_path)

    assert cfg.name == "taipei-demo"
    assert cfg.hotspot_percentile == 90
    assert cfg.weights["lst"] == 0.5
    assert cfg.buffer_distances_m == [0, 100, 300, 500]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -q`
Expected: `ModuleNotFoundError` or `ImportError` for `urbancanopy.config`

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(slots=True)
class RunConfig:
    name: str
    aoi_path: Path
    start_date: str
    end_date: str
    hotspot_percentile: int
    weights: dict[str, float]
    buffer_distances_m: list[int]
    scenario_canopy_delta_pct: float


def load_run_config(path: Path) -> RunConfig:
    raw = yaml.safe_load(path.read_text())
    return RunConfig(
        name=raw["name"],
        aoi_path=Path(raw["aoi_path"]),
        start_date=raw["start_date"],
        end_date=raw["end_date"],
        hotspot_percentile=int(raw["hotspot_percentile"]),
        weights={k: float(v) for k, v in raw["weights"].items()},
        buffer_distances_m=[int(v) for v in raw["buffer_distances_m"]],
        scenario_canopy_delta_pct=float(raw["scenario_canopy_delta_pct"]),
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -q`
Expected: `1 passed`

**Step 5: Commit**

```bash
git add backend/pyproject.toml backend/urbancanopy/__init__.py backend/urbancanopy/config.py backend/tests/test_config.py backend/configs/taipei-demo.yml backend/data/inputs/.gitkeep backend/data/outputs/.gitkeep
git commit -m "chore: initialize urban cooling backend"
```

### Task 2: Add AOI loading and STAC search with primary/fallback catalogs

**Files:**
- Create: `backend/urbancanopy/aoi.py`
- Create: `backend/urbancanopy/stac.py`
- Create: `backend/tests/test_stac.py`
- Create: `backend/tests/fixtures/taipei_aoi.geojson`
- Modify: `backend/urbancanopy/config.py`

**Step 1: Write the failing test**

```python
from urbancanopy.stac import search_items


class FailingClient:
    def search(self, **_: object) -> object:
        raise RuntimeError("primary unavailable")


class WorkingClient:
    def __init__(self) -> None:
        self.called = False

    def search(self, **_: object) -> object:
        self.called = True
        return ["item-1", "item-2"]


def test_search_items_falls_back_to_secondary_catalog() -> None:
    secondary = WorkingClient()

    items = search_items(
        collection="landsat-c2-l2",
        bbox=(121.4, 24.9, 121.7, 25.2),
        date_range="2025-06-01/2025-08-31",
        clients=[FailingClient(), secondary],
    )

    assert items == ["item-1", "item-2"]
    assert secondary.called is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_stac.py -q`
Expected: missing `search_items`

**Step 3: Write minimal implementation**

```python
from collections.abc import Sequence


def search_items(
    *,
    collection: str,
    bbox: tuple[float, float, float, float],
    date_range: str,
    clients: Sequence[object],
) -> list[object]:
    last_error: Exception | None = None
    for client in clients:
        try:
            return list(
                client.search(
                    collections=[collection],
                    bbox=bbox,
                    datetime=date_range,
                )
            )
        except Exception as exc:  # pragma: no cover - exercised by test
            last_error = exc
    raise RuntimeError("all STAC catalogs failed") from last_error
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_stac.py -q`
Expected: `1 passed`

**Step 5: Commit**

```bash
git add backend/urbancanopy/aoi.py backend/urbancanopy/stac.py backend/tests/test_stac.py backend/tests/fixtures/taipei_aoi.geojson backend/urbancanopy/config.py
git commit -m "feat: add AOI loading and STAC fallback search"
```

### Task 3: Implement Sentinel-2 and Landsat preprocessing helpers

**Files:**
- Create: `backend/urbancanopy/masking.py`
- Create: `backend/tests/test_masking.py`
- Modify: `backend/urbancanopy/stac.py`

**Step 1: Write the failing test**

```python
import numpy as np
import xarray as xr

from urbancanopy.masking import apply_binary_mask, seasonal_median


def test_apply_binary_mask_sets_invalid_pixels_to_nan() -> None:
    data = xr.DataArray(np.array([[1.0, 2.0], [3.0, 4.0]]), dims=("y", "x"))
    valid = xr.DataArray(np.array([[1, 0], [1, 1]]), dims=("y", "x"))

    masked = apply_binary_mask(data, valid)

    assert float(masked.values[0, 0]) == 1.0
    assert np.isnan(masked.values[0, 1])


def test_seasonal_median_reduces_time_dimension() -> None:
    cube = xr.DataArray(
        np.array([
            [[1.0, 3.0], [5.0, 7.0]],
            [[2.0, 4.0], [6.0, 8.0]],
        ]),
        dims=("time", "y", "x"),
    )

    composite = seasonal_median(cube)

    assert composite.dims == ("y", "x")
    assert float(composite.values[0, 0]) == 1.5
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_masking.py -q`
Expected: missing preprocessing helpers

**Step 3: Write minimal implementation**

```python
import xarray as xr


def apply_binary_mask(data: xr.DataArray, valid_mask: xr.DataArray) -> xr.DataArray:
    return data.where(valid_mask.astype(bool))


def seasonal_median(data: xr.DataArray) -> xr.DataArray:
    return data.median(dim="time", skipna=True)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_masking.py -q`
Expected: `2 passed`

**Step 5: Commit**

```bash
git add backend/urbancanopy/masking.py backend/tests/test_masking.py backend/urbancanopy/stac.py
git commit -m "feat: add raster masking and compositing helpers"
```

### Task 4: Compute NDVI, EVI, NDBI, and LST hotspot masks

**Files:**
- Create: `backend/urbancanopy/indices.py`
- Create: `backend/urbancanopy/thermal.py`
- Create: `backend/tests/test_indices.py`
- Create: `backend/tests/test_thermal.py`

**Step 1: Write the failing tests**

```python
import numpy as np
import xarray as xr

from urbancanopy.indices import compute_ndvi, compute_ndbi
from urbancanopy.thermal import hotspot_mask


def test_compute_ndvi_matches_expected_ratio() -> None:
    nir = xr.DataArray(np.array([[0.8, 0.6]]), dims=("y", "x"))
    red = xr.DataArray(np.array([[0.2, 0.3]]), dims=("y", "x"))

    ndvi = compute_ndvi(nir=nir, red=red)

    assert np.allclose(ndvi.values, [[0.6, 0.33333333]])


def test_hotspot_mask_marks_top_percentile_pixels() -> None:
    lst = xr.DataArray(np.array([[28.0, 31.0], [34.0, 36.0]]), dims=("y", "x"))

    mask = hotspot_mask(lst, percentile=75)

    assert mask.values.tolist() == [[False, False], [False, True]]
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_indices.py tests/test_thermal.py -q`
Expected: missing modules/functions

**Step 3: Write minimal implementation**

```python
import xarray as xr


def compute_ndvi(*, nir: xr.DataArray, red: xr.DataArray) -> xr.DataArray:
    return (nir - red) / (nir + red)


def compute_ndbi(*, swir: xr.DataArray, nir: xr.DataArray) -> xr.DataArray:
    return (swir - nir) / (swir + nir)
```

```python
import numpy as np
import xarray as xr


def hotspot_mask(lst: xr.DataArray, percentile: int) -> xr.DataArray:
    threshold = float(np.nanpercentile(lst.values, percentile))
    return lst >= threshold
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_indices.py tests/test_thermal.py -q`
Expected: `3 passed` after adding an EVI coverage test before moving on

**Step 5: Commit**

```bash
git add backend/urbancanopy/indices.py backend/urbancanopy/thermal.py backend/tests/test_indices.py backend/tests/test_thermal.py
git commit -m "feat: derive vegetation indices and LST hotspots"
```

### Task 5: Score planting priority and vectorize candidate zones

**Files:**
- Create: `backend/urbancanopy/scoring.py`
- Create: `backend/urbancanopy/vectorize.py`
- Create: `backend/tests/test_scoring.py`
- Create: `backend/tests/test_vectorize.py`

**Step 1: Write the failing tests**

```python
import numpy as np
import xarray as xr

from urbancanopy.scoring import priority_score


def test_priority_score_combines_heat_green_and_built_layers() -> None:
    lst = xr.DataArray(np.array([[30.0, 40.0]]), dims=("y", "x"))
    ndvi = xr.DataArray(np.array([[0.8, 0.1]]), dims=("y", "x"))
    ndbi = xr.DataArray(np.array([[0.2, 0.9]]), dims=("y", "x"))

    score = priority_score(lst=lst, ndvi=ndvi, ndbi=ndbi, weights={"lst": 0.5, "green": 0.3, "built": 0.2})

    assert score.values[0, 1] > score.values[0, 0]
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scoring.py tests/test_vectorize.py -q`
Expected: missing scoring/vectorization modules

**Step 3: Write minimal implementation**

```python
import xarray as xr


def normalize(data: xr.DataArray) -> xr.DataArray:
    return (data - data.min()) / (data.max() - data.min())


def priority_score(*, lst: xr.DataArray, ndvi: xr.DataArray, ndbi: xr.DataArray, weights: dict[str, float]) -> xr.DataArray:
    return (
        weights["lst"] * normalize(lst)
        + weights["green"] * (1 - normalize(ndvi))
        + weights["built"] * normalize(ndbi)
    )
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scoring.py tests/test_vectorize.py -q`
Expected: `2 passed`; then add one more failing test for minimum polygon area filtering before refining `vectorize.py`

**Step 5: Commit**

```bash
git add backend/urbancanopy/scoring.py backend/urbancanopy/vectorize.py backend/tests/test_scoring.py backend/tests/test_vectorize.py
git commit -m "feat: score and vectorize priority planting zones"
```

### Task 6: Add park interior vs buffer analysis with bootstrap uncertainty

**Files:**
- Create: `backend/urbancanopy/parks.py`
- Create: `backend/tests/test_parks.py`

**Step 1: Write the failing test**

```python
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
    assert summary.loc[0, "ci_low_c"] < summary.loc[0, "delta_lst_c"] < summary.loc[0, "ci_high_c"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_parks.py -q`
Expected: missing `pci_summary`

**Step 3: Write minimal implementation**

```python
import numpy as np
import pandas as pd


def pci_summary(samples: pd.DataFrame, *, inner_buffer: int, outer_buffer: int, n_boot: int, seed: int) -> pd.DataFrame:
    park = samples.loc[samples["buffer_m"] == inner_buffer, "lst_c"].to_numpy()
    ring = samples.loc[samples["buffer_m"] == outer_buffer, "lst_c"].to_numpy()
    delta = float(np.median(ring) - np.median(park))

    rng = np.random.default_rng(seed)
    boot = []
    for _ in range(n_boot):
        boot.append(float(np.median(rng.choice(ring, len(ring), replace=True)) - np.median(rng.choice(park, len(park), replace=True))))

    return pd.DataFrame(
        {
            "delta_lst_c": [delta],
            "ci_low_c": [float(np.percentile(boot, 2.5))],
            "ci_high_c": [float(np.percentile(boot, 97.5))],
        }
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_parks.py -q`
Expected: `1 passed`

**Step 5: Commit**

```bash
git add backend/urbancanopy/parks.py backend/tests/test_parks.py
git commit -m "feat: add park cooling evidence analysis"
```

### Task 7: Implement canopy-change scenario bands and export contracts

**Files:**
- Create: `backend/urbancanopy/scenario.py`
- Create: `backend/urbancanopy/exports.py`
- Create: `backend/tests/test_scenario.py`
- Create: `backend/tests/test_exports.py`

**Step 1: Write the failing tests**

```python
import numpy as np
import xarray as xr

from urbancanopy.scenario import apply_canopy_scenario


def test_apply_canopy_scenario_returns_low_mid_high_temperature_bands() -> None:
    lst = xr.DataArray(np.array([[35.0]]), dims=("y", "x"))

    bands = apply_canopy_scenario(lst=lst, canopy_delta_pct=10)

    assert float(bands["low"].values[0, 0]) == 34.9
    assert float(bands["mid"].values[0, 0]) == 34.4
    assert float(bands["high"].values[0, 0]) == 32.7
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scenario.py tests/test_exports.py -q`
Expected: missing modules/functions

**Step 3: Write minimal implementation**

```python
import xarray as xr


COEFFICIENTS = {"low": 0.01, "mid": 0.06, "high": 0.23}


def apply_canopy_scenario(*, lst: xr.DataArray, canopy_delta_pct: float) -> dict[str, xr.DataArray]:
    return {
        label: lst - (beta * canopy_delta_pct)
        for label, beta in COEFFICIENTS.items()
    }
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scenario.py tests/test_exports.py -q`
Expected: `2 passed` after adding an export-schema test for `priority_zones.geojson` fields

**Step 5: Commit**

```bash
git add backend/urbancanopy/scenario.py backend/urbancanopy/exports.py backend/tests/test_scenario.py backend/tests/test_exports.py
git commit -m "feat: add canopy cooling scenarios and exports"
```

### Task 8: Wire the CLI, orchestrate the pipeline, and document usage

**Files:**
- Create: `backend/urbancanopy/cli.py`
- Create: `backend/tests/test_cli.py`
- Create: `backend/notebooks/mvp_pipeline.ipynb`
- Create: `backend/methodology.md`
- Modify: `backend/pyproject.toml`

**Step 1: Write the failing test**

```python
from pathlib import Path

from urbancanopy.cli import run_pipeline


def test_run_pipeline_writes_expected_artifacts(tmp_path: Path, monkeypatch) -> None:
    output_dir = tmp_path / "outputs"
    monkeypatch.setattr("urbancanopy.cli.execute_pipeline", lambda *_args, **_kwargs: {
        "priority_geojson": output_dir / "priority_zones.geojson",
        "summary_csv": output_dir / "district_summary.csv",
    })

    outputs = run_pipeline(config_path=Path("configs/taipei-demo.yml"), output_dir=output_dir)

    assert outputs["priority_geojson"].name == "priority_zones.geojson"
    assert outputs["summary_csv"].name == "district_summary.csv"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -q`
Expected: missing CLI entrypoint

**Step 3: Write minimal implementation**

```python
from pathlib import Path


def execute_pipeline(*, config_path: Path, output_dir: Path) -> dict[str, Path]:
    raise NotImplementedError


def run_pipeline(*, config_path: Path, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    return execute_pipeline(config_path=config_path, output_dir=output_dir)
```

After the test is green, replace `NotImplementedError` in `execute_pipeline` by composing the real modules in this order: config -> AOI -> STAC -> masking/composite -> indices/thermal -> scoring/vectorize -> parks -> scenario -> exports.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -q`
Expected: `1 passed`

Then run the full suite:

Run: `pytest tests -q`
Expected: all backend tests pass

**Step 5: Commit**

```bash
git add backend/urbancanopy/cli.py backend/tests/test_cli.py backend/notebooks/mvp_pipeline.ipynb backend/methodology.md backend/pyproject.toml
git commit -m "feat: add runnable urban cooling pipeline"
```

### Task 9: Add one smoke integration path for a real AOI config

**Files:**
- Create: `backend/tests/test_integration_smoke.py`
- Modify: `backend/configs/taipei-demo.yml`
- Modify: `backend/methodology.md`

**Step 1: Write the failing test**

```python
import pytest


@pytest.mark.integration
def test_demo_config_is_well_formed() -> None:
    from urbancanopy.config import load_run_config

    cfg = load_run_config("configs/taipei-demo.yml")

    assert cfg.hotspot_percentile == 90
    assert cfg.buffer_distances_m == [0, 100, 300, 500]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_integration_smoke.py -q`
Expected: config-path handling failure or missing fixture until path normalization is added

**Step 3: Write minimal implementation**

Normalize string paths in `load_run_config`, keep the smoke test offline-only, and document a separate manual live-data command in `backend/methodology.md`:

```bash
python -m urbancanopy.cli --config configs/taipei-demo.yml --output-dir data/outputs/taipei-demo
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_integration_smoke.py -q`
Expected: `1 passed`

**Step 5: Commit**

```bash
git add backend/tests/test_integration_smoke.py backend/configs/taipei-demo.yml backend/methodology.md
git commit -m "test: add offline smoke coverage for demo config"
```

## Notes for the implementing engineer

- Keep all live STAC client creation in one place inside `backend/urbancanopy/stac.py`; every other module should accept ready-made xarray/geopandas objects so tests stay offline.
- Do not use Sentinel-3 or ERA5 in the first runnable path; leave them as optional context hooks after Landsat + Sentinel-2 outputs work end-to-end.
- Export domain-correct fields first: `priority_score`, `lst_c`, `hotspot_flag`, `ndvi`, `ndbi`, `cooling_low_c`, `cooling_mid_c`, `cooling_high_c`, and confidence metadata. Frontend field mapping is a later task.
- Keep park buffering in a projected CRS, not EPSG:4326 degrees.
- Keep notebook scope narrow: one run, one AOI, one map, one evidence plot. The CLI is the primary product surface for this phase.
