# Urban Canopy Methodology

This document tracks the technical execution of the multicity cooling pipeline.

## Running the Pipeline

Today, the checked-in multicity demo path is intentionally offline-first: it validates configuration, CLI wiring, and demo execution without requiring live remote data access.

The default offline pipeline check is:

```bash
pytest -m integration -q
```

When the live data loaders are finished, the planned manual CLI command is:

```bash
python -m urbancanopy.cli --config configs/multicity-demo.yml --output-dir data/outputs/multicity-demo
```

For explicit provider probe verification during live-mode work, run a targeted source load and confirm a `dataset.probe.succeeded` or `dataset.probe.failed` event is recorded with `provider`, `source_key`, and probe detail metadata. The current backend split is:

- Copernicus probes for Sentinel-2 and Sentinel-3
- Open Data Cube probes for Landsat

For the current offline smoke/integration verification path, run:

```bash
pytest -m integration -q
```

## Completion Checks

Before calling the backend slice complete, verify all of the following:

1. **Offline pipeline check**
   - Run the offline integration path and confirm outputs are written without contacting live providers.
   - Expect explicit `dataset.probe.failed` events for skipped offline-demo probes and `fallback.activated` events for demo surface layers or unavailable live access.

2. **Live provider probe check**
   - Run a live provider probe against each configured source and confirm the logger records one probe event per source.
   - `dataset.probe.succeeded` means the provider returned at least one item.
   - `dataset.probe.failed` means the request errored, returned no items, or the system intentionally skipped the probe because the run stayed offline.

3. **Degraded or fallback conditions**
   - The run is degraded whenever `fallbackUsed` is `true` for a probe or a `fallback.activated` event is emitted.
   - Offline demo mode counts as degraded by design because live probes are skipped and offline artifacts stand in for provider data.
   - A probe that returns no items also counts as fallback/degraded because the pipeline cannot rely on live coverage for that source.

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
