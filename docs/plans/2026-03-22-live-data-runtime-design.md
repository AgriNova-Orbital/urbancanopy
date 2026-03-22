# Live Data Runtime Design

## Problem

The backend currently exposes datasource labels that the frontend can rely on, but the runtime path is not fully honest:

- `copernicus` and `opendatacube` are the datasource labels in config and API-facing behavior.
- `backend/urbancanopy/sources.py` currently routes both implemented live lookups through Planetary Computer STAC.
- `sentinel3` is explicitly fallback-only today.
- offline demo runs emit probe failures, but they do not cleanly distinguish skipped probes from true live failures.

This creates a mismatch between the datasource contract the frontend sees and the transport behavior the backend actually executes.

## Goals

- Keep datasource labels stable for backend/frontend integration.
- Make probe results honest and testable for both named datasources: `copernicus` and `opendatacube`.
- Clearly distinguish `live_success`, `live_failure_fallback`, and `offline_demo_skip` in logs and status output.
- Make CLI behavior predictable in both online and offline flows.
- Update methodology only where needed to reflect the real provider state.

## Non-Goals

- Redesigning frontend UI or frontend datasource contracts.
- Reworking the whole geospatial processing pipeline.
- Pretending unsupported or not-yet-true live transports are complete.

## Chosen Approach

Keep datasource identifiers as the stable contract and add a separate runtime-truth layer to probe results.

Every provider probe should report:

- `datasource`: stable label exposed to the rest of the system
- `actual_transport`: the upstream path actually used by the code today
- `status`: `live_success`, `live_failure_fallback`, or `offline_demo_skip`
- `capability`: `working_now`, `fallback_only`, or `needs_fix`
- `detail`: short human-readable explanation

This preserves compatibility while making runtime behavior explicit.

## Current Expected Truth Table

For the current codebase, the runtime should report these states honestly unless implementation work changes them:

| source_key | datasource | current runtime truth |
| --- | --- | --- |
| `sentinel2` | `copernicus` | real live probe path exists and may report `working_now` when probe succeeds |
| `sentinel3` | `copernicus` | fallback-only today |
| `landsat` | `opendatacube` | datasource label remains ODC, but if the call is not a true ODC path it must report `needs_fix` or equivalent honest transport metadata |

## Runtime Contract Changes

### `backend/urbancanopy/sources.py`

- Refine `dataset_probe_result()` so it derives event and log level from explicit probe status, not just `ok` and `fallback_used`.
- Add helper logic for probe metadata so every source reports the same schema.
- Ensure catalog clients can report both declared datasource and actual transport.
- Keep `dataset.probe.succeeded` reserved for real live success only.
- Use `dataset.probe.failed` for real probe attempts that fail and trigger fallback or degraded behavior.
- Introduce `dataset.probe.skipped` for offline/demo skips so those are not misclassified as live failures.

### Capability reporting

- `working_now`: live probe path exists and succeeds.
- `fallback_only`: source is intentionally not live-backed today.
- `needs_fix`: source claims a datasource contract that is not yet satisfied by the real live implementation.

This makes provider state consumable by logs, status APIs, and manual verification.

## CLI Behavior

### `backend/urbancanopy/cli.py`

- Separate provider probing from offline artifact generation.
- Offline demo mode should emit one `dataset.probe.skipped` event per configured source.
- Offline demo mode should emit `fallback.activated` only for the actual use of demo layers or demo artifacts.
- Live or probe-oriented execution should attempt each configured source once, producing one honest result per source.
- Synthetic/offline outputs must never imply successful live provider access.

## Logging and Degraded Semantics

- `live_success`: no fallback for that source, info-level success.
- `live_failure_fallback`: live attempt failed and runtime degraded to fallback, warning/error plus `fallback.activated`.
- `offline_demo_skip`: probe intentionally skipped because the run stayed offline, warning-level skip without implying a network failure.

Required metadata fields on probe events:

- `source_key`
- `datasource`
- `actual_transport`
- `status`
- `capability`
- `detail`

Optional metadata should still include useful context such as `bbox`, `item_count`, `error`, or skip reason.

## Testing Strategy

Provider-facing automated tests should stay deterministic and prove classification behavior without requiring live network access.

### Files in scope

- `backend/tests/test_dataset_probe.py`
- `backend/tests/test_sources.py`
- `backend/tests/test_cli.py`

### Required automated coverage

- Probe event classification for success, failure-with-fallback, and offline skip.
- Honest capability reporting for `sentinel2`, `sentinel3`, and `landsat`.
- CLI offline demo path still produces outputs and logs skip/degraded states correctly.
- Live probe helpers do not mark fake successes when synthetic outputs are used.

### Required manual verification

- Exercise at least one real live provider probe and record its honest result.
- Report both named datasource outcomes:
  - `copernicus`
  - `opendatacube`
- If one datasource remains fallback-only or still maps to a non-true transport, the manual verification must say so explicitly instead of treating it as passing live support.

## Documentation Changes

Update `backend/methodology.md` only where needed:

- keep datasource labels as the backend/frontend contract
- document actual current live transport behavior honestly
- document the distinction between live success, live failure with fallback, and offline demo skip
- document the minimum verification commands and expected interpretation of results

## Implementation Notes

- Favor small, test-first changes in `sources.py` and `cli.py`.
- Preserve current config compatibility.
- Do not introduce UI-facing schema churn unless required to expose the new truth fields in backend status/logging paths.
