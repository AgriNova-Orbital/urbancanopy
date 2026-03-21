# Urban Canopy Methodology

This document tracks the technical execution of the multicity cooling pipeline.

## Running the Pipeline

Today, the checked-in multicity demo path is intentionally offline-first: it validates configuration, CLI wiring, and demo execution without requiring live remote data access.

When the live data loaders are finished, the planned manual CLI command is:

```bash
python -m urbancanopy.cli --config configs/multicity-demo.yml --output-dir data/outputs/multicity-demo
```

For the current offline smoke/integration verification path, run:

```bash
pytest -m integration -q
```

## Live API Split

The backend intentionally keeps the live-source split explicit based on provider capabilities:

1. **Copernicus API**
   - Sourced: **Sentinel-2** for greenness and built-up layers, and **Sentinel-3** for metro-scale comparison.
   - Why: Copernicus Data Space catalogs are the planned live source for these Sentinel products.

2. **Open Data Cube API**
   - Sourced: **Landsat surface temperature** and future indexed products.
   - Why: Open Data Cube is the planned live path for analysis-ready thermal and indexed raster products.

## Current Status

The present repository state does not yet execute the full live data ingestion path end to end. The offline/demo flow is the supported path today, while the Copernicus and Open Data Cube integrations above describe the intended production data split as live loaders are completed.

## Integration Testing

Tests marked with `@pytest.mark.integration` remain offline-only unless a test explicitly says otherwise. The multicity smoke test loads the real `configs/multicity-demo.yml` configuration from the `backend` directory context to catch config-path drift without contacting Copernicus or Open Data Cube services.
