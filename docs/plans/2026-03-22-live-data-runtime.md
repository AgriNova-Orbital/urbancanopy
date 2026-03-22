# Live Data Runtime Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make backend datasource probing honest and testable for `copernicus` and `opendatacube`, while keeping offline demo behavior predictable and clearly classified.

**Architecture:** Keep datasource labels stable for the backend/frontend contract, but split them from runtime truth in probe metadata. Centralize probe classification in `backend/urbancanopy/sources.py`, route CLI behavior through explicit probe/offline paths in `backend/urbancanopy/cli.py`, and prove the behavior with deterministic provider-facing tests plus one documented manual live probe path.

**Tech Stack:** Python 3.11, `pytest`, `pystac-client`, `odc-stac`, `xarray`, `geopandas`, existing backend logger/event store

---

### Task 1: Normalize probe outcome classification

**Files:**
- Modify: `backend/urbancanopy/sources.py`
- Modify: `backend/tests/test_dataset_probe.py`

**Step 1: Write the failing test**

Add these tests to `backend/tests/test_dataset_probe.py`:

```python
from urbancanopy.sources import dataset_probe_result


def test_dataset_probe_result_reports_live_success() -> None:
    result = dataset_probe_result(
        provider="copernicus",
        source_key="sentinel2",
        status="live_success",
        detail="catalog probe succeeded",
        capability="working_now",
        actual_transport="planetary_computer_stac",
    )

    assert result["event"] == "dataset.probe.succeeded"
    assert result["level"] == "info"
    assert result["fallbackUsed"] is False
    assert result["meta"]["status"] == "live_success"


def test_dataset_probe_result_reports_live_failure_with_fallback() -> None:
    result = dataset_probe_result(
        provider="opendatacube",
        source_key="landsat",
        status="live_failure_fallback",
        detail="catalog probe failed",
        capability="needs_fix",
        actual_transport="planetary_computer_stac",
    )

    assert result["event"] == "dataset.probe.failed"
    assert result["fallbackUsed"] is True
    assert result["meta"]["capability"] == "needs_fix"


def test_dataset_probe_result_reports_offline_demo_skip() -> None:
    result = dataset_probe_result(
        provider="copernicus",
        source_key="sentinel3",
        status="offline_demo_skip",
        detail="live dataset probe skipped in offline demo mode",
        capability="fallback_only",
        actual_transport="not_attempted",
    )

    assert result["event"] == "dataset.probe.skipped"
    assert result["level"] == "warning"
    assert result["fallbackUsed"] is True
    assert result["meta"]["actual_transport"] == "not_attempted"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_dataset_probe.py -q`
Expected: FAIL because `dataset_probe_result()` does not yet accept `status`, `capability`, or `actual_transport`, and cannot emit `dataset.probe.skipped`.

**Step 3: Write minimal implementation**

Update `backend/urbancanopy/sources.py` so `dataset_probe_result()` accepts explicit runtime classification:

```python
def dataset_probe_result(
    *,
    provider: str,
    source_key: str,
    status: str,
    detail: str,
    capability: str,
    actual_transport: str,
    run_id: str | None = None,
    mode: str = "offline",
    online: bool | None = None,
    meta: dict[str, object] | None = None,
) -> dict[str, object]:
    probe_meta = {
        "provider": provider,
        "datasource": provider,
        "source_key": source_key,
        "status": status,
        "capability": capability,
        "actual_transport": actual_transport,
        "detail": detail,
    }
    if meta is not None:
        probe_meta.update(meta)

    if status == "live_success":
        level = "info"
        event = "dataset.probe.succeeded"
        fallback_used = False
    elif status == "offline_demo_skip":
        level = "warning"
        event = "dataset.probe.skipped"
        fallback_used = True
    else:
        level = "warning"
        event = "dataset.probe.failed"
        fallback_used = True

    return build_event(
        level=level,
        event=event,
        component="sources",
        message=detail,
        run_id=run_id,
        mode=mode,
        online=online,
        fallback_used=fallback_used,
        meta=probe_meta,
    )
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_dataset_probe.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/urbancanopy/sources.py backend/tests/test_dataset_probe.py
git commit -m "test: classify dataset probe outcomes honestly"
```

### Task 2: Make source clients report honest datasource capability

**Files:**
- Modify: `backend/urbancanopy/sources.py`
- Modify: `backend/tests/test_sources.py`

**Step 1: Write the failing test**

Add tests like these to `backend/tests/test_sources.py`:

```python
def test_sentinel3_reports_fallback_only_probe_status(tmp_path: Path) -> None:
    logger = UrbancanopyLogger.create(base_dir=tmp_path, timestamp="2026-03-22_14-00-00")
    clients = build_catalog_clients(
        {
            "sentinel2": "copernicus",
            "sentinel3": "copernicus",
            "landsat": "opendatacube",
        },
        logger=logger,
        run_id="run-1",
        mode="live_probe",
    )

    with pytest.raises(LiveAccessNotImplementedError):
        clients["sentinel3"].load(logger=logger, run_id="run-1", mode="live_probe")

    event = logger.store.list_recent_events(limit=1)[0]
    assert event["event"] == "dataset.probe.failed"
    assert event["meta"]["capability"] == "fallback_only"
    assert event["meta"]["status"] == "live_failure_fallback"


def test_landsat_probe_reports_actual_transport_when_not_true_odc(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    logger = UrbancanopyLogger.create(base_dir=tmp_path, timestamp="2026-03-22_14-01-00")
    clients = build_catalog_clients(
        {
            "sentinel2": "copernicus",
            "sentinel3": "copernicus",
            "landsat": "opendatacube",
        }
    )

    monkeypatch.setattr(OpenDataCubeClient, "_search_items", lambda self, bbox: ["mock-item"])
    monkeypatch.setattr("odc.stac.load", lambda *args, **kwargs: xr.DataArray([1], dims=["x"]))

    clients["landsat"].load((121.5, 25.0, 121.6, 25.1), logger=logger, run_id="run-1", mode="live_probe")

    event = logger.store.list_recent_events(limit=1)[0]
    assert event["event"] == "dataset.probe.succeeded"
    assert event["meta"]["datasource"] == "opendatacube"
    assert event["meta"]["actual_transport"]
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_sources.py -q`
Expected: FAIL because current source clients do not emit uniform `status`, `capability`, and `actual_transport` metadata.

**Step 3: Write minimal implementation**

Refactor `backend/urbancanopy/sources.py` to give each client honest runtime metadata:

```python
@dataclass(slots=True)
class CatalogClient:
    source_key: str
    provider: str

    @property
    def datasource(self) -> str:
        return self.provider

    @property
    def actual_transport(self) -> str:
        return "not_implemented"

    @property
    def capability(self) -> str:
        return "fallback_only"


@dataclass(slots=True)
class CopernicusStacClient(CatalogClient):
    collection: str

    @property
    def actual_transport(self) -> str:
        return "planetary_computer_stac"

    @property
    def capability(self) -> str:
        if self.source_key == "sentinel3":
            return "fallback_only"
        return "working_now"


@dataclass(slots=True)
class OpenDataCubeClient(CatalogClient):
    product: str

    @property
    def actual_transport(self) -> str:
        return "planetary_computer_stac"

    @property
    def capability(self) -> str:
        return "needs_fix"
```

Then thread those properties through every `dataset_probe_result()` call so success/failure metadata is truthful for `sentinel2`, `sentinel3`, and `landsat`.

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_sources.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/urbancanopy/sources.py backend/tests/test_sources.py
git commit -m "feat: report honest live datasource capability"
```

### Task 3: Separate offline demo skips from live probing in the CLI

**Files:**
- Modify: `backend/urbancanopy/cli.py`
- Modify: `backend/tests/test_cli.py`

**Step 1: Write the failing test**

Add tests like these to `backend/tests/test_cli.py`:

```python
def test_run_pipeline_offline_demo_logs_probe_skips_not_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("urbancanopy.cli._load_city_boundary", lambda _city: _synthetic_boundary())
    monkeypatch.setattr("urbancanopy.cli.export_priority_zones", _write_priority_geojson)
    monkeypatch.setattr("urbancanopy.cli.export_city_comparison", lambda df, path, **_kwargs: df.to_csv(path, index=False))
    monkeypatch.setattr("urbancanopy.cli.export_city_signature", lambda df, path, **_kwargs: df.to_csv(path, index=False))
    monkeypatch.setattr("urbancanopy.cli.export_park_cooling", lambda df, path, **_kwargs: df.to_csv(path, index=False))

    run_pipeline(
        config_path=Path("configs/multicity-demo.yml"),
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path,
        log_timestamp="2026-03-22_14-10-00",
    )

    store = EventStore(tmp_path / "2026-03-22_14-10-00_events.db")
    events = store.list_recent_events(limit=100)
    assert any(event["event"] == "dataset.probe.skipped" for event in events)
    assert not any(
        event["event"] == "dataset.probe.failed"
        and event["meta"].get("status") == "offline_demo_skip"
        for event in events
    )


def test_execute_pipeline_probe_only_attempts_live_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempted = []

    def _record_load(self, bbox=(0, 0, 0, 0), *, logger=None, run_id=None, mode="offline"):
        attempted.append((self.source_key, mode))
        return xr.DataArray([1], dims=["x"])

    monkeypatch.setattr("urbancanopy.cli._load_city_boundary", lambda _city: _synthetic_boundary())
    monkeypatch.setattr("urbancanopy.sources.CopernicusStacClient.load", _record_load)
    monkeypatch.setattr("urbancanopy.sources.OpenDataCubeClient.load", _record_load)

    execute_pipeline(
        config_path=Path("configs/multicity-demo.yml"),
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path,
        log_timestamp="2026-03-22_14-11-00",
        mode="live_probe",
        probe_only=True,
    )

    assert attempted
    assert all(mode == "live_probe" for _, mode in attempted)
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_cli.py -q`
Expected: FAIL because offline demo still logs skipped probes as failures and the CLI has no explicit probe-only/live-probe path.

**Step 3: Write minimal implementation**

Update `backend/urbancanopy/cli.py` to split probing from output generation:

```python
def _probe_catalog_clients(
    *,
    clients: Mapping[str, CatalogClient],
    bbox: tuple[float, float, float, float],
    logger: UrbancanopyLogger,
    run_id: str,
    mode: str,
) -> None:
    for client in clients.values():
        try:
            client.load(bbox, logger=logger, run_id=run_id, mode=mode)
        except Exception:
            continue


def execute_pipeline(
    *,
    config_path: Path,
    output_dir: Path,
    log_dir: Path | None = None,
    log_timestamp: str | None = None,
    mode: str | None = None,
    probe_only: bool = False,
) -> dict[str, Path]:
    ...
    if resolved_mode == "offline_demo":
        _log_offline_probe_skips(...)
    else:
        _probe_catalog_clients(...)

    if probe_only:
        return {}
```

Also update `main()` to accept explicit mode controls, for example:

```python
parser.add_argument(
    "--mode",
    choices=["offline", "offline_demo", "live_probe"],
    default=None,
)
parser.add_argument("--probe-only", action="store_true")
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_cli.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/urbancanopy/cli.py backend/tests/test_cli.py
git commit -m "feat: separate live probing from offline demo runtime"
```

### Task 4: Update methodology to match real provider behavior

**Files:**
- Modify: `backend/methodology.md`

**Step 1: Write the failing test**

Add or update a doc assertion in an existing provider-facing test file, for example in `backend/tests/test_cli.py`:

```python
def test_methodology_documents_honest_live_provider_status() -> None:
    text = Path("methodology.md").read_text(encoding="utf-8")

    assert "live_success" in text
    assert "live_failure_fallback" in text
    assert "offline_demo_skip" in text
    assert "copernicus" in text
    assert "opendatacube" in text
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_cli.py::test_methodology_documents_honest_live_provider_status -q`
Expected: FAIL because `backend/methodology.md` does not yet document the new status vocabulary and current datasource truth clearly enough.

**Step 3: Write minimal implementation**

Update `backend/methodology.md` to state:

```markdown
- `copernicus` and `opendatacube` remain the datasource labels used by the backend contract.
- `live_success` means a real live probe succeeded.
- `live_failure_fallback` means the live attempt failed and the system degraded to fallback behavior.
- `offline_demo_skip` means the probe was intentionally skipped because the run stayed offline.
- Current source truth must be reported honestly per source, including fallback-only or needs-fix states.
```

Also document the manual verification commands for:

- dataset-probe test suite
- offline demo run
- live probe execution for both named datasources

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_cli.py::test_methodology_documents_honest_live_provider_status -q`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/methodology.md backend/tests/test_cli.py
git commit -m "docs: describe honest live datasource behavior"
```

## Verification Commands

Run these before calling the slice complete:

```bash
cd backend && pytest tests/test_dataset_probe.py tests/test_sources.py tests/test_cli.py -q
cd backend && pytest tests/test_cli.py::test_run_pipeline_writes_real_offline_demo_outputs -q
cd backend && python -m urbancanopy.cli --config configs/multicity-demo.yml --output-dir ../tmp/live-probe --mode live_probe --probe-only
```

Interpret the live probe results honestly:

- `dataset.probe.succeeded` = real live success
- `dataset.probe.failed` + `status=live_failure_fallback` = live path attempted but degraded/fell back
- `dataset.probe.skipped` + `status=offline_demo_skip` = offline/demo skip, not a network failure

Record the observed result for both named datasources:

- `copernicus`
- `opendatacube`

If `opendatacube` still runs through a non-ODC transport or remains degraded, keep that result explicit in the PR notes instead of calling it complete live support.
