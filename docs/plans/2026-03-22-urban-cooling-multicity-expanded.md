# Urban Cooling Multicity Platform Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a dual-track MVP that uses Copernicus and Open Data Cube APIs to compare inside-vs-outside urban heat across Taipei, Tokyo, London, and New York, while also producing neighborhood-scale planting priority zones for one focus city.

**Architecture:** Split the backend into two linked products. Track A is a metro-scale comparison pipeline using Sentinel-3 plus city-core and outer-ring geometries to produce cross-city summer heat signatures. Track B is an actionable focus-city pipeline using Landsat surface temperature from an ODC-accessible source plus Sentinel-2 greenness/built-up layers from Copernicus to score planting priority zones, park cooling evidence, and canopy-cooling scenarios. Keep ingestion behind source adapters so the same analytics can run against Copernicus-hosted data or Open Data Cube-backed products without rewriting business logic.

**Tech Stack:** Python 3.11, `pytest`, `pystac-client`, `odc-stac`, `datacube`, `xarray`, `rioxarray`, `geopandas`, `rasterio`, `numpy`, `pandas`, `shapely`, `pyyaml`, `matplotlib`

---

This plan expands `docs/plans/2026-03-22-urban-cooling-python-pipeline.md` with the CTO guidance: use Copernicus + Open Data Cube APIs, add Sentinel-3 inside/outside city comparison, and support a four-city comparison set (`taipei`, `tokyo`, `london`, `new_york`). Default assumption: Taipei is the focus city for block-level planting recommendations; the other three cities are comparison cases unless later expanded.

### Task 1: Bootstrap a multicity backend config model

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/urbancanopy/__init__.py`
- Create: `backend/urbancanopy/config.py`
- Create: `backend/tests/test_config.py`
- Create: `backend/configs/multicity-demo.yml`
- Create: `backend/data/inputs/.gitkeep`
- Create: `backend/data/outputs/.gitkeep`

**Step 1: Write the failing test**

```python
from pathlib import Path

from urbancanopy.config import load_run_config


def test_load_run_config_supports_focus_and_comparison_cities(tmp_path: Path) -> None:
    config_path = tmp_path / "run.yml"
    config_path.write_text(
        """
name: multicity-demo
focus_city: taipei
comparison_cities: [taipei, tokyo, london, new_york]
catalogs:
  sentinel2: copernicus
  sentinel3: copernicus
  landsat: opendatacube
summer_window:
  start_date: 2025-06-01
  end_date: 2025-08-31
hotspot_percentile: 90
weights:
  lst: 0.5
  green: 0.3
  built: 0.2
buffer_distances_m: [0, 100, 300, 500]
comparison_ring_km: [0, 5, 20]
scenario_canopy_delta_pct: 10
""".strip()
    )

    cfg = load_run_config(config_path)

    assert cfg.focus_city == "taipei"
    assert cfg.comparison_cities == ["taipei", "tokyo", "london", "new_york"]
    assert cfg.catalogs["landsat"] == "opendatacube"
    assert cfg.comparison_ring_km == [0, 5, 20]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -q`
Expected: `ModuleNotFoundError` or missing `load_run_config`

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(slots=True)
class RunConfig:
    name: str
    focus_city: str
    comparison_cities: list[str]
    catalogs: dict[str, str]
    summer_window: dict[str, str]
    hotspot_percentile: int
    weights: dict[str, float]
    buffer_distances_m: list[int]
    comparison_ring_km: list[int]
    scenario_canopy_delta_pct: float


def load_run_config(path: str | Path) -> RunConfig:
    raw = yaml.safe_load(Path(path).read_text())
    return RunConfig(
        name=raw["name"],
        focus_city=raw["focus_city"],
        comparison_cities=list(raw["comparison_cities"]),
        catalogs=dict(raw["catalogs"]),
        summer_window=dict(raw["summer_window"]),
        hotspot_percentile=int(raw["hotspot_percentile"]),
        weights={k: float(v) for k, v in raw["weights"].items()},
        buffer_distances_m=[int(v) for v in raw["buffer_distances_m"]],
        comparison_ring_km=[int(v) for v in raw["comparison_ring_km"]],
        scenario_canopy_delta_pct=float(raw["scenario_canopy_delta_pct"]),
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -q`
Expected: `1 passed`

**Step 5: Commit**

```bash
git add backend/pyproject.toml backend/urbancanopy/__init__.py backend/urbancanopy/config.py backend/tests/test_config.py backend/configs/multicity-demo.yml backend/data/inputs/.gitkeep backend/data/outputs/.gitkeep
git commit -m "chore: initialize multicity cooling backend"
```

### Task 2: Add source adapters for Copernicus and Open Data Cube

**Files:**
- Create: `backend/urbancanopy/sources.py`
- Create: `backend/tests/test_sources.py`
- Modify: `backend/urbancanopy/config.py`

**Step 1: Write the failing test**

```python
from urbancanopy.sources import build_catalog_clients


def test_build_catalog_clients_uses_copernicus_for_sentinel_and_odc_for_landsat() -> None:
    clients = build_catalog_clients(
        {
            "sentinel2": "copernicus",
            "sentinel3": "copernicus",
            "landsat": "opendatacube",
        }
    )

    assert clients["sentinel2"].name == "copernicus"
    assert clients["sentinel3"].name == "copernicus"
    assert clients["landsat"].name == "opendatacube"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_sources.py -q`
Expected: missing `build_catalog_clients`

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass


@dataclass(slots=True)
class CatalogClient:
    name: str


def build_catalog_clients(catalogs: dict[str, str]) -> dict[str, CatalogClient]:
    return {key: CatalogClient(name=value) for key, value in catalogs.items()}
```

After the first green test, extend `CatalogClient` into two real adapters:
- `CopernicusStacClient` for Sentinel-2 and Sentinel-3 item search/load metadata
- `OpenDataCubeClient` for Landsat product discovery/loading through `odc-stac` or `datacube`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_sources.py -q`
Expected: `1 passed`

**Step 5: Commit**

```bash
git add backend/urbancanopy/sources.py backend/tests/test_sources.py backend/urbancanopy/config.py
git commit -m "feat: add Copernicus and ODC source adapters"
```

### Task 3: Add city registry and inside/outside comparison geometry builders

**Files:**
- Create: `backend/urbancanopy/cities.py`
- Create: `backend/tests/test_cities.py`
- Create: `backend/tests/fixtures/cities/taipei.geojson`
- Create: `backend/tests/fixtures/cities/tokyo.geojson`
- Create: `backend/tests/fixtures/cities/london.geojson`
- Create: `backend/tests/fixtures/cities/new_york.geojson`

**Step 1: Write the failing test**

```python
import geopandas as gpd
from shapely.geometry import Polygon

from urbancanopy.cities import build_comparison_zones


def test_build_comparison_zones_returns_core_and_outer_ring() -> None:
    city = gpd.GeoDataFrame(
        {"city": ["taipei"]},
        geometry=[Polygon([(0, 0), (4, 0), (4, 4), (0, 4)])],
        crs="EPSG:3857",
    )

    zones = build_comparison_zones(city, inner_km=0, outer_km=5, exclude_core_to_km=1)

    assert set(zones["zone"]) == {"urban_core", "outer_ring"}
    assert zones.loc[zones["zone"] == "outer_ring", "geometry"].iloc[0].area > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cities.py -q`
Expected: missing comparison geometry builder

**Step 3: Write minimal implementation**

```python
import geopandas as gpd
import pandas as pd


def build_comparison_zones(city_gdf: gpd.GeoDataFrame, *, inner_km: int, outer_km: int, exclude_core_to_km: int) -> gpd.GeoDataFrame:
    core = city_gdf.copy()
    core["zone"] = "urban_core"

    outer = city_gdf.copy()
    outer.geometry = city_gdf.buffer(outer_km * 1000).difference(city_gdf.buffer(exclude_core_to_km * 1000))
    outer["zone"] = "outer_ring"

    return gpd.GeoDataFrame(
        pd.concat([core[["zone", "geometry"]], outer[["zone", "geometry"]]], ignore_index=True),
        crs=city_gdf.crs,
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cities.py -q`
Expected: `1 passed`

**Step 5: Commit**

```bash
git add backend/urbancanopy/cities.py backend/tests/test_cities.py backend/tests/fixtures/cities/taipei.geojson backend/tests/fixtures/cities/tokyo.geojson backend/tests/fixtures/cities/london.geojson backend/tests/fixtures/cities/new_york.geojson
git commit -m "feat: add multicity boundary and comparison geometry support"
```

### Task 4: Implement raster masking and seasonal compositing helpers

**Files:**
- Create: `backend/urbancanopy/masking.py`
- Create: `backend/tests/test_masking.py`

**Step 1: Write the failing tests**

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

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_masking.py -q`
Expected: missing masking helpers

**Step 3: Write minimal implementation**

```python
import xarray as xr


def apply_binary_mask(data: xr.DataArray, valid_mask: xr.DataArray) -> xr.DataArray:
    return data.where(valid_mask.astype(bool))


def seasonal_median(data: xr.DataArray) -> xr.DataArray:
    return data.median(dim="time", skipna=True)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_masking.py -q`
Expected: `2 passed`

**Step 5: Commit**

```bash
git add backend/urbancanopy/masking.py backend/tests/test_masking.py
git commit -m "feat: add raster masking and compositing helpers"
```

### Task 5: Add Sentinel-3 inside-vs-outside city comparison summaries

**Files:**
- Create: `backend/urbancanopy/comparison.py`
- Create: `backend/tests/test_comparison.py`

**Step 1: Write the failing test**

```python
import pandas as pd

from urbancanopy.comparison import summarize_city_heat_gap


def test_summarize_city_heat_gap_computes_core_minus_outer_delta() -> None:
    samples = pd.DataFrame(
        {
            "city": ["taipei"] * 6,
            "zone": ["urban_core", "urban_core", "urban_core", "outer_ring", "outer_ring", "outer_ring"],
            "lst_c": [34.0, 34.2, 33.8, 31.0, 31.4, 31.2],
        }
    )

    summary = summarize_city_heat_gap(samples)

    assert summary.loc[0, "city"] == "taipei"
    assert summary.loc[0, "heat_gap_c"] > 2.5
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_comparison.py -q`
Expected: missing `summarize_city_heat_gap`

**Step 3: Write minimal implementation**

```python
import pandas as pd


def summarize_city_heat_gap(samples: pd.DataFrame) -> pd.DataFrame:
    grouped = samples.groupby(["city", "zone"])["lst_c"].median().unstack()
    grouped["heat_gap_c"] = grouped["urban_core"] - grouped["outer_ring"]
    return grouped.reset_index()[["city", "heat_gap_c"]]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_comparison.py -q`
Expected: `1 passed`

**Step 5: Commit**

```bash
git add backend/urbancanopy/comparison.py backend/tests/test_comparison.py
git commit -m "feat: add Sentinel-3 city comparison summaries"
```

### Task 6: Compute Sentinel-2 greenness and Landsat heat layers for the focus city

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
git commit -m "feat: add focus-city heat and vegetation layers"
```

### Task 7: Build a simple cross-city cooling signature model

**Files:**
- Create: `backend/urbancanopy/modeling.py`
- Create: `backend/tests/test_modeling.py`

**Step 1: Write the failing test**

```python
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

    assert table.loc[table["city"] == "taipei", "signature_score"].iloc[0] > table.loc[table["city"] == "tokyo", "signature_score"].iloc[0]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_modeling.py -q`
Expected: missing city-signature model

**Step 3: Write minimal implementation**

```python
import pandas as pd


def _normalize(series: pd.Series) -> pd.Series:
    return (series - series.min()) / (series.max() - series.min())


def build_city_signature_table(metrics: pd.DataFrame) -> pd.DataFrame:
    scored = metrics.copy()
    scored["signature_score"] = (
        0.5 * _normalize(scored["heat_gap_c"])
        + 0.3 * (1 - _normalize(scored["mean_ndvi"]))
        + 0.2 * _normalize(scored["mean_ndbi"])
    )
    return scored.sort_values("signature_score", ascending=False).reset_index(drop=True)
```

This is intentionally not framed as serious machine learning. It is an explainable comparative model for the hackathon pitch.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_modeling.py -q`
Expected: `1 passed`

**Step 5: Commit**

```bash
git add backend/urbancanopy/modeling.py backend/tests/test_modeling.py
git commit -m "feat: add cross-city cooling signature model"
```

### Task 8: Score planting priority zones for the focus city and vectorize outputs

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
git commit -m "feat: score and vectorize planting priority zones"
```

### Task 9: Add park interior vs buffer evidence analysis for exemplar parks

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
git commit -m "feat: add exemplar park cooling analysis"
```

### Task 10: Add canopy scenario bands and export contracts

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
Expected: `2 passed` after adding an export-schema test for `priority_zones.geojson`, `city_comparison.csv`, and `city_signature.csv`

**Step 5: Commit**

```bash
git add backend/urbancanopy/scenario.py backend/urbancanopy/exports.py backend/tests/test_scenario.py backend/tests/test_exports.py
git commit -m "feat: add scenario bands and multicity exports"
```

### Task 11: Wire a CLI that runs both tracks end-to-end

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


def test_run_pipeline_returns_focus_city_and_multicity_outputs(tmp_path: Path, monkeypatch) -> None:
    output_dir = tmp_path / "outputs"
    monkeypatch.setattr(
        "urbancanopy.cli.execute_pipeline",
        lambda *_args, **_kwargs: {
            "priority_geojson": output_dir / "priority_zones.geojson",
            "city_comparison_csv": output_dir / "city_comparison.csv",
            "city_signature_csv": output_dir / "city_signature.csv",
        },
    )

    outputs = run_pipeline(config_path=Path("configs/multicity-demo.yml"), output_dir=output_dir)

    assert outputs["priority_geojson"].name == "priority_zones.geojson"
    assert outputs["city_comparison_csv"].name == "city_comparison.csv"
    assert outputs["city_signature_csv"].name == "city_signature.csv"
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

After the test is green, replace `NotImplementedError` by composing the real modules in this order: config -> source adapters -> city registry -> Sentinel-3 comparison -> focus-city Landsat/Sentinel-2 analysis -> city signature model -> scenarios -> exports.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -q`
Expected: `1 passed`

Then run the full suite:

Run: `pytest tests -q`
Expected: all backend tests pass

**Step 5: Commit**

```bash
git add backend/urbancanopy/cli.py backend/tests/test_cli.py backend/notebooks/mvp_pipeline.ipynb backend/methodology.md backend/pyproject.toml
git commit -m "feat: add runnable multicity cooling pipeline"
```

### Task 12: Add offline smoke tests and document the live API paths

**Files:**
- Create: `backend/tests/test_integration_smoke.py`
- Modify: `backend/configs/multicity-demo.yml`
- Modify: `backend/methodology.md`

**Step 1: Write the failing test**

```python
import pytest

from urbancanopy.config import load_run_config


@pytest.mark.integration
def test_multicity_demo_config_is_well_formed() -> None:
    cfg = load_run_config("configs/multicity-demo.yml")

    assert cfg.focus_city == "taipei"
    assert cfg.comparison_cities == ["taipei", "tokyo", "london", "new_york"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_integration_smoke.py -q`
Expected: config-path handling failure until path normalization is added

**Step 3: Write minimal implementation**

Normalize string paths in `load_run_config`, keep this test offline-only, and document two manual live-data commands in `backend/methodology.md`:

```bash
python -m urbancanopy.cli --config configs/multicity-demo.yml --output-dir data/outputs/multicity-demo
pytest -m integration -q
```

Document the live-source split explicitly:
- Copernicus API for Sentinel-2 and Sentinel-3
- Open Data Cube API for Landsat surface temperature and any future indexed products

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_integration_smoke.py -q`
Expected: `1 passed`

**Step 5: Commit**

```bash
git add backend/tests/test_integration_smoke.py backend/configs/multicity-demo.yml backend/methodology.md
git commit -m "test: add smoke coverage for multicity demo config"
```

## Notes for the implementing engineer

- Keep the product narrative honest: Sentinel-3 is for metro-scale inside/outside comparison, not neighborhood planting decisions.
- Keep Taipei as the default focus city unless the user explicitly changes it; that keeps the MVP feasible while still answering the CTO's request for four-city comparison.
- The "model" for the comparison track should stay explainable and small-sample-safe. Do not overclaim machine learning with only four cities.
- Use projected CRSs for all buffer creation and park analysis.
- Export both decision-support and storytelling artifacts: `priority_zones.geojson`, `district_summary.csv`, `city_comparison.csv`, `city_signature.csv`, and one `park_cooling.csv`.
- Keep all live API code in `backend/urbancanopy/sources.py` so the rest of the pipeline stays testable offline.
