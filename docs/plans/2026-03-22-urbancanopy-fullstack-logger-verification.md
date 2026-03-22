# Urbancanopy Fullstack Logger Verification

This checklist stays scoped to final local-first logging verification for Task 12.

## Workspace

Run all commands from this worktree:

```bash
cd /Users/ben001109/Desktop/work/urbancanopy/.worktrees/fullstack-logger
```

Set a reusable timestamp so the root `logs/` writes are easy to inspect:

```bash
export UC_LOG_TS="2026-03-22_23-30-00"
```

## Backend tests

```bash
cd backend && env PATH="/Users/ben001109/Desktop/work/urbancanopy/backend/.venv/bin:$PATH" pytest tests -q
```

This command is the required full-backend check even though unrelated GeoJSON export environment issues can still block `tests/test_exports.py` in this workstation setup.

## Frontend checks

Use the verified contract and typecheck path while `npm run build` is blocked by the known Next 14 and Node 25 incompatibility. Do not report the build as passing unless that upstream issue is resolved first.

```bash
cd frontend && node tests/logger-contract.mjs && npx tsc --noEmit
```

If you want to confirm the current build failure mode explicitly, run this separately and expect it to stay blocked for now:

```bash
cd frontend && npm run build
```

## Offline pipeline run

This command keeps the verification focused on logging by swapping in lightweight file writers for the export steps while still writing backend logs and the SQLite event DB into the worktree root `logs/` directory.

```bash
cd backend && env PATH="/Users/ben001109/Desktop/work/urbancanopy/backend/.venv/bin:$PATH" UC_LOG_TS="$UC_LOG_TS" python - <<'PY'
import os
import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

import urbancanopy.cli as cli
from urbancanopy.cli import run_pipeline


def synthetic_boundary():
    return gpd.GeoDataFrame(geometry=[box(121.5, 25.0, 121.6, 25.1)], crs="EPSG:4326")


def write_priority_geojson(zones, path: Path, **_kwargs):
    features = []
    for index, (geometry, priority_score) in enumerate(
        zip(zones.geometry, zones["priority_score"], strict=False),
        start=1,
    ):
        features.append(
            {
                "type": "Feature",
                "properties": {"zone_id": f"zone-{index}", "priority_score": float(priority_score)},
                "geometry": geometry.__geo_interface__,
            }
        )
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")


cli.export_priority_zones = write_priority_geojson
cli.export_city_comparison = lambda df, path, **_kwargs: df.to_csv(path, index=False)
cli.export_city_signature = lambda df, path, **_kwargs: df.to_csv(path, index=False)
cli.export_park_cooling = lambda df, path, **_kwargs: df.to_csv(path, index=False)
cli._load_city_boundary = lambda _city: synthetic_boundary()

run_pipeline(
    config_path=Path("configs/multicity-demo.yml"),
    output_dir=Path("../tmp/fullstack-logger-offline"),
    log_timestamp=os.environ["UC_LOG_TS"],
)
PY
```

## Live provider probe

This checks that live probe events are emitted for each configured source. Success means a `dataset.probe.succeeded` event or an expected logged failure/fallback event is written for every source.

```bash
cd backend && env PATH="/Users/ben001109/Desktop/work/urbancanopy/backend/.venv/bin:$PATH" UC_LOG_TS="$UC_LOG_TS-live" python - <<'PY'
import os

from urbancanopy.config import load_run_config
from urbancanopy.logger import UrbancanopyLogger
from urbancanopy.sources import build_catalog_clients

cfg = load_run_config("configs/multicity-demo.yml")
logger = UrbancanopyLogger.create(timestamp=os.environ["UC_LOG_TS"])
clients = build_catalog_clients(
    {key: str(value) for key, value in cfg.catalogs.items()},
    logger=logger,
    run_id="live-probe",
    mode="live_probe",
)

for source_key, client in clients.items():
    try:
        client.load(
            (121.5, 25.0, 121.6, 25.1),
            logger=logger,
            run_id="live-probe",
            mode="live_probe",
        )
    except Exception as exc:
        print(f"{source_key}: {type(exc).__name__}: {exc}")
    else:
        print(f"{source_key}: ok")
PY
```

## Status endpoint check

This reads the status snapshot directly from the backend app against the root `logs/` directory.

```bash
cd backend && env PATH="/Users/ben001109/Desktop/work/urbancanopy/backend/.venv/bin:$PATH" python - <<'PY'
import json
from pathlib import Path

from fastapi.testclient import TestClient

from urbancanopy.status_api import create_app

client = TestClient(create_app(base_dir=Path("../logs")))
print(json.dumps(client.get("/api/status").json(), indent=2))
PY
```

## Confirm root logs writes

```bash
cd backend && env PATH="/Users/ben001109/Desktop/work/urbancanopy/backend/.venv/bin:$PATH" UC_LOG_TS="$UC_LOG_TS" python - <<'PY'
import os
import json
import sqlite3
from pathlib import Path

root_logs = Path("../logs")
timestamp = os.environ["UC_LOG_TS"]
paths = sorted(str(path) for path in root_logs.glob(f"{timestamp}*"))
print(json.dumps(paths, indent=2))

db_path = root_logs / f"{timestamp}_events.db"
with sqlite3.connect(db_path) as connection:
    event_count = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]

print(json.dumps({"eventDb": str(db_path), "eventCount": event_count}, indent=2))
PY
```
