# Urban Canopy Methodology

This document tracks the current, checked-in runtime behavior for the multicity cooling pipeline.

## Datasource Contract vs Runtime Truth

The backend/frontend datasource contract stays stable even when the live transport is incomplete.

- Stable datasource labels: `copernicus` and `opendatacube`
- These labels are the contract exposed in probe metadata as `datasource`
- Actual runtime transport is reported separately as `actual_transport`

Current source truth:

- sentinel2: datasource `copernicus`, capability `working_now`, actual transport `planetary_computer_stac`
- sentinel3: datasource `copernicus`, capability `fallback_only`, actual transport `not_implemented`
- landsat: datasource `opendatacube`, capability `needs_fix`, actual transport `planetary_computer_stac`

## Runtime Modes

- `offline`: no live probe attempt; the run stays fully offline and may optionally stop after skip logging with `--probe-only`
- `offline_demo`: the demo path intentionally skips live probing and writes synthetic/demo outputs
- `live_probe`: attempts real source probes; use `--probe-only` to stop after probe logging

`live_probe` is currently probe-only by design. It is for verifying provider/runtime truth, not for generating the offline demo artifacts.

## Status and Event Meanings

Dataset probe events must be read together with `status`, `capability`, and `actual_transport`.

- `dataset.probe.succeeded` + `live_success`: a real live probe succeeded
- `dataset.probe.failed` + `live_failure`: a live probe was attempted and failed without using fallback/demo artifacts
- `dataset.probe.failed` + `live_failure_fallback`: a live attempt degraded into fallback behavior in a runtime that actually uses fallback outputs
- `dataset.probe.skipped` + `offline_demo_skip`: the probe was intentionally skipped because the run stayed in `offline` or `offline_demo`

Current fallback semantics:

- Offline skips are not network failures
- Live failures are honest probe failures or not-yet-implemented live paths
- `fallback.activated` is used for degraded demo/output behavior, not for probe-only verification runs

## Verification Commands

Run these from `backend/`.

Provider-facing dataset probe tests:

```bash
pytest tests/test_dataset_probe.py tests/test_sources.py tests/test_cli.py -q
```

Offline demo path:

```bash
pytest tests/test_cli.py::test_run_pipeline_writes_real_offline_demo_outputs -q
```

Manual offline demo run:

```bash
python -m urbancanopy.cli --config configs/multicity-demo.yml --output-dir ../tmp/offline-demo --mode offline_demo
```

Live probe path:

```bash
python -m urbancanopy.cli --config configs/multicity-demo.yml --output-dir ../tmp/live-probe --mode live_probe --probe-only
```

Read the live probe results per datasource label:

- `copernicus`: verify the Sentinel probe events honestly show `working_now` for `sentinel2` and `fallback_only` for `sentinel3`
- `opendatacube`: verify the Landsat probe events still report datasource `opendatacube` while current capability remains `needs_fix`

When reading live probe output, keep the datasource contract separate from transport truth:

- `copernicus` remains the datasource label for Sentinel probes even when one source is fallback-only
- `opendatacube` remains the datasource label for Landsat even though the current live transport is still `planetary_computer_stac`

## Current Support Statement

The supported checked-in workflow today is the offline and offline-demo path. Live probing is implemented to report honest runtime truth, but full end-to-end live production loading is not complete for every datasource-backed source.
