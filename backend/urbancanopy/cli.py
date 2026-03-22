from pathlib import Path
from uuid import uuid4
import zlib

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr

from urbancanopy.aggregation import aggregate_city_metrics
from urbancanopy.cities import get_city_fixture_path, build_comparison_zones
from urbancanopy.comparison import (
    build_modeling_ready_city_metrics,
    summarize_city_heat_gap,
)
from urbancanopy.config import load_run_config
from urbancanopy.exports import (
    export_city_comparison,
    export_city_signature,
    export_park_cooling,
    export_priority_zones,
)
from urbancanopy.logger import UrbancanopyLogger
from urbancanopy.modeling import build_city_signature_table
from urbancanopy.parks import pci_summary
from urbancanopy.scoring import priority_score
from urbancanopy.sources import build_catalog_clients
from urbancanopy.vectorize import vectorize_priority_cells


def _seed_for(name: str) -> int:
    return zlib.crc32(name.encode("utf-8")) & 0xFFFFFFFF


def _load_city_boundary(city: str) -> gpd.GeoDataFrame:
    return gpd.read_file(get_city_fixture_path(city))


def _grid_from_boundary(
    city: str, boundary: gpd.GeoDataFrame
) -> tuple[np.ndarray, np.ndarray]:
    min_x, min_y, max_x, max_y = boundary.total_bounds
    seed = _seed_for(city)
    x = np.linspace(min_x, max_x, 6)
    y = np.linspace(max_y, min_y, 6)

    x_shift = ((seed % 7) - 3) * 0.00005
    y_shift = (((seed // 7) % 7) - 3) * 0.00005
    return x + x_shift, y + y_shift


def _surface_layers(
    city: str, boundary: gpd.GeoDataFrame
) -> tuple[xr.DataArray, xr.DataArray, xr.DataArray]:
    x, y = _grid_from_boundary(city, boundary)
    xx, yy = np.meshgrid(np.linspace(0.0, 1.0, len(x)), np.linspace(0.0, 1.0, len(y)))
    seed = _seed_for(city)

    lst = 29.0 + (seed % 5) + 3.5 * xx + 2.5 * yy
    ndvi = np.clip(0.62 - 0.22 * xx - 0.12 * yy + (seed % 3) * 0.015, 0.05, 0.85)
    ndbi = np.clip(0.28 + 0.32 * xx + 0.18 * yy + ((seed // 11) % 3) * 0.02, 0.05, 0.95)

    attrs = {
        "crs": str(boundary.crs or "EPSG:4326"),
        "x_resolution": float(abs(x[1] - x[0])) if len(x) > 1 else 0.01,
        "y_resolution": float(abs(y[0] - y[1])) if len(y) > 1 else 0.01,
    }
    coords = {"y": y, "x": x}

    return (
        xr.DataArray(lst, dims=("y", "x"), coords=coords, attrs=attrs),
        xr.DataArray(ndvi, dims=("y", "x"), coords=coords, attrs=attrs),
        xr.DataArray(ndbi, dims=("y", "x"), coords=coords, attrs=attrs),
    )


def _city_zone_samples(city: str, boundary: gpd.GeoDataFrame) -> pd.DataFrame:
    seed = _seed_for(city)
    zones = build_comparison_zones(
        boundary,
        inner_km=0,
        outer_km=20,
        exclude_core_to_km=5,
    )
    rows: list[dict[str, float | str]] = []

    for zone in zones["zone"].tolist():
        base = 30.5 + (seed % 6) * 0.35
        if zone == "urban_core":
            values = [base + 1.5, base + 1.8, base + 2.1]
        else:
            values = [base - 0.6, base - 0.4, base - 0.2]
        for value in values:
            rows.append({"city": city, "zone": zone, "lst_c": round(value, 3)})

    return pd.DataFrame(rows)


def _park_samples(city: str, buffer_distances_m: list[int]) -> pd.DataFrame:
    inner_buffer = buffer_distances_m[0]
    outer_buffer = next(
        (distance for distance in buffer_distances_m if distance > inner_buffer),
        inner_buffer,
    )
    seed = _seed_for(city)
    rows: list[dict[str, float | str]] = []

    for park_index in range(1, 4):
        park_id = f"{city}-park-{park_index}"
        baseline = 31.0 + park_index * 0.4 + (seed % 4) * 0.2
        for offset in (0.0, 0.2, 0.35, 0.5):
            rows.append(
                {
                    "park_id": park_id,
                    "buffer_m": inner_buffer,
                    "lst_c": round(baseline - 0.9 + offset, 3),
                }
            )
            rows.append(
                {
                    "park_id": park_id,
                    "buffer_m": outer_buffer,
                    "lst_c": round(baseline + 0.5 + offset, 3),
                }
            )

    return pd.DataFrame(rows)


def _sort_by_city_order(frame: pd.DataFrame, city_order: list[str]) -> pd.DataFrame:
    ordered = frame.copy()
    ordered["city"] = pd.Categorical(
        ordered["city"], categories=city_order, ordered=True
    )
    return ordered.sort_values("city").reset_index(drop=True)


def _require_outputs(outputs: dict[str, Path]) -> dict[str, Path]:
    missing = [path for path in outputs.values() if not path.exists()]
    if missing:
        names = ", ".join(path.name for path in missing)
        raise FileNotFoundError(f"expected pipeline outputs were not created: {names}")
    return outputs


def _mode_for_config(config_path: Path, config_name: str | None = None) -> str:
    marker = config_name or config_path.stem
    if "demo" in marker:
        return "offline_demo"
    return "offline"


def _build_run_id(log_timestamp: str | None) -> str:
    if log_timestamp is not None:
        return log_timestamp
    return f"run-{uuid4().hex[:12]}"


def execute_pipeline(
    *,
    config_path: Path,
    output_dir: Path,
    log_dir: Path | None = None,
    log_timestamp: str | None = None,
) -> dict[str, Path]:
    logger = UrbancanopyLogger.create(base_dir=log_dir, timestamp=log_timestamp)
    run_id = _build_run_id(log_timestamp)
    mode = _mode_for_config(config_path)

    try:
        cfg = load_run_config(config_path)
        mode = _mode_for_config(config_path, cfg.name)
        logger.info(
            event="mode.changed",
            component="cli",
            message=f"pipeline mode set to {mode}",
            run_id=run_id,
            mode=mode,
            fallback_used=mode == "offline_demo",
            meta={"config_path": config_path, "output_dir": output_dir},
        )
        logger.info(
            event="pipeline.started",
            component="cli",
            message="pipeline starting",
            run_id=run_id,
            mode=mode,
            fallback_used=mode == "offline_demo",
            meta={"config_path": config_path, "output_dir": output_dir},
        )
        build_catalog_clients(
            {key: str(value) for key, value in cfg.catalogs.items()},
            logger=logger,
            run_id=run_id,
            mode=mode,
        )
        if mode == "offline_demo":
            logger.warning(
                event="dataset.probe.failed",
                component="cli",
                message="live dataset probes skipped in offline demo mode",
                run_id=run_id,
                mode=mode,
                fallback_used=True,
                meta={"reason": "offline_demo"},
            )

        city_samples: list[pd.DataFrame] = []
        surface_context: list[pd.DataFrame] = []
        focus_layers: tuple[xr.DataArray, xr.DataArray, xr.DataArray] | None = None

        for city in cfg.comparison_cities:
            boundary = _load_city_boundary(city)
            lst, ndvi, ndbi = _surface_layers(city, boundary)
            logger.warning(
                event="fallback.activated",
                component="cli",
                message="using offline demo surface layers",
                run_id=run_id,
                mode=mode,
                fallback_used=True,
                meta={"city": city},
            )
            city_samples.append(_city_zone_samples(city, boundary))
            surface_context.append(aggregate_city_metrics(city, ndvi, ndbi))

            if city == cfg.focus_city:
                focus_layers = (lst, ndvi, ndbi)

        if focus_layers is None:
            raise ValueError(
                f"focus city boundary could not be prepared: {cfg.focus_city}"
            )

        city_comparison = summarize_city_heat_gap(
            pd.concat(city_samples, ignore_index=True)
        )
        city_comparison = _sort_by_city_order(city_comparison, cfg.comparison_cities)
        modeling_ready = build_modeling_ready_city_metrics(
            city_comparison,
            pd.concat(surface_context, ignore_index=True),
        )
        city_signature = build_city_signature_table(modeling_ready)

        focus_lst, focus_ndvi, focus_ndbi = focus_layers
        score = priority_score(
            lst=focus_lst,
            ndvi=focus_ndvi,
            ndbi=focus_ndbi,
            weights=cfg.weights,
        )
        score.attrs.update(focus_lst.attrs)
        threshold = float(np.quantile(score.values, cfg.hotspot_percentile / 100.0))
        priority_gdf = vectorize_priority_cells(score, threshold=threshold)

        park_samples = _park_samples(cfg.focus_city, cfg.buffer_distances_m)
        inner_buffer = cfg.buffer_distances_m[0]
        outer_buffer = next(
            distance for distance in cfg.buffer_distances_m if distance > inner_buffer
        )
        park_cooling = pci_summary(
            park_samples,
            inner_buffer=inner_buffer,
            outer_buffer=outer_buffer,
            n_boot=250,
            seed=_seed_for(cfg.focus_city),
        )

        priority_geojson = output_dir / "priority_zones.geojson"
        city_comparison_csv = output_dir / "city_comparison.csv"
        city_signature_csv = output_dir / "city_signature.csv"
        park_cooling_csv = output_dir / "park_cooling.csv"

        export_priority_zones(
            priority_gdf,
            priority_geojson,
            logger=logger,
            run_id=run_id,
            mode=mode,
        )
        export_city_comparison(
            city_comparison,
            city_comparison_csv,
            logger=logger,
            run_id=run_id,
            mode=mode,
        )
        export_city_signature(
            city_signature,
            city_signature_csv,
            logger=logger,
            run_id=run_id,
            mode=mode,
        )
        export_park_cooling(
            park_cooling,
            park_cooling_csv,
            logger=logger,
            run_id=run_id,
            mode=mode,
        )

        outputs = _require_outputs(
            {
                "priority_geojson": priority_geojson,
                "city_comparison_csv": city_comparison_csv,
                "city_signature_csv": city_signature_csv,
                "park_cooling_csv": park_cooling_csv,
            }
        )
        logger.info(
            event="pipeline.completed",
            component="cli",
            message="pipeline completed",
            run_id=run_id,
            mode=mode,
            fallback_used=mode == "offline_demo",
            meta={"outputs": outputs},
        )
        return outputs
    except Exception as exc:
        logger.error(
            event="pipeline.failed",
            component="cli",
            message="pipeline failed",
            run_id=run_id,
            mode=mode,
            fallback_used=mode == "offline_demo",
            meta={
                "error": str(exc),
                "config_path": config_path,
                "output_dir": output_dir,
            },
        )
        raise


def run_pipeline(
    *,
    config_path: Path,
    output_dir: Path,
    log_dir: Path | None = None,
    log_timestamp: str | None = None,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    return execute_pipeline(
        config_path=config_path,
        output_dir=output_dir,
        log_dir=log_dir,
        log_timestamp=log_timestamp,
    )


def main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Run Urban Cooling Pipeline")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    try:
        run_pipeline(config_path=args.config, output_dir=args.output_dir)
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
