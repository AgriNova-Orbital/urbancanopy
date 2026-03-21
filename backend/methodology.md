# Urban Canopy Methodology

This document tracks the technical execution of the multicity cooling pipeline.

## Running the Pipeline

You can run the full end-to-end pipeline (when live data is implemented) with:

```bash
uv run urbancanopy --config configs/multicity-demo.yml --output-dir data/outputs/multicity-demo
```

Or run offline verification tests using:

```bash
uv run pytest -m integration -q
```

## Live API Split

The backend intentionally splits imagery sourcing based on the API capabilities of the public providers:

1. **Copernicus API**
   - Sourced: **Sentinel-2** (greenness/built-up layers), **Sentinel-3** (metro-scale comparison)
   - Why: High-resolution canopy and urban core measurements work well directly from the Copernicus Data Space Ecosystem STAC catalogs.

2. **Open Data Cube API**
   - Sourced: **Landsat 8/9** (surface temperature) and any future indexed products
   - Why: Time-series analysis for thermal hotspots relies on Analysis Ready Data (ARD). The Open Data Cube interface (`odc-stac`/`datacube`) ensures efficient pixel-level alignment and masking.

## Integration Testing

Tests marked with `@pytest.mark.integration` load actual configurations (like `multicity-demo.yml`) without necessarily contacting the live APIs unless specified. These run during continuous integration to catch config drift.
