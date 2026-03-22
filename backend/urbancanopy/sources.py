from dataclasses import dataclass

import pystac_client
import planetary_computer
import odc.stac
import xarray as xr

from urbancanopy.logging_schema import build_event


def _log_event(logger, level: str, **event_fields: object) -> None:
    if logger is None:
        return
    getattr(logger, level)(**event_fields)


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
    if status not in {
        "live_success",
        "live_failure",
        "live_failure_fallback",
        "offline_demo_skip",
    }:
        raise ValueError(f"Unsupported dataset probe status: {status}")

    probe_meta: dict[str, object] = {
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
    elif status == "live_failure":
        level = "warning"
        event = "dataset.probe.failed"
        fallback_used = False
    elif status == "offline_demo_skip":
        level = "warning"
        event = "dataset.probe.skipped"
        fallback_used = False
    else:
        level = "warning"
        event = "dataset.probe.failed"
        fallback_used = True

    message = detail if detail else "dataset probe completed"

    return build_event(
        level=level,
        event=event,
        component="sources",
        message=message,
        run_id=run_id,
        mode=mode,
        online=online,
        fallback_used=fallback_used,
        meta=probe_meta,
    )


def _log_probe_result(logger, probe: dict[str, object]) -> dict[str, object]:
    if logger is None:
        return probe

    getattr(logger, str(probe["level"]))(
        event=probe["event"],
        component=probe["component"],
        message=probe["message"],
        run_id=probe.get("runId"),
        job_id=probe.get("jobId"),
        mode=probe.get("mode"),
        online=probe.get("online"),
        fallback_used=bool(probe.get("fallbackUsed")),
        meta=probe.get("meta"),
    )
    return probe


def _ensure_dataset(data: xr.Dataset | xr.DataArray) -> xr.Dataset:
    if isinstance(data, xr.Dataset):
        return data
    return data.to_dataset(name=data.name or "data")


class LiveAccessNotImplementedError(RuntimeError):
    def __init__(self, source_key: str) -> None:
        super().__init__(
            f"Live catalog access is not implemented for source '{source_key}'"
        )


@dataclass(slots=True)
class CatalogClient:
    source_key: str
    provider: str

    @property
    def name(self) -> str:
        return self.provider

    @property
    def capability(self) -> str:
        return "fallback_only"

    @property
    def actual_transport(self) -> str:
        return "not_implemented"

    def load(
        self,
        bbox: tuple[float, float, float, float] = (0, 0, 0, 0),
        *,
        logger=None,
        run_id: str | None = None,
        mode: str = "offline",
    ) -> xr.Dataset:
        status = "live_failure" if mode == "live_probe" else "live_failure_fallback"
        detail = (
            "live catalog access unavailable"
            if mode == "live_probe"
            else "live catalog access unavailable; fallback required"
        )
        _log_probe_result(
            logger,
            dataset_probe_result(
                provider=self.provider,
                source_key=self.source_key,
                status=status,
                detail=detail,
                capability=self.capability,
                actual_transport=self.actual_transport,
                run_id=run_id,
                mode=mode,
                meta={"bbox": bbox},
            ),
        )
        if mode != "live_probe":
            _log_event(
                logger,
                "warning",
                event="fallback.activated",
                component="sources",
                message=detail,
                run_id=run_id,
                mode=mode,
                fallback_used=True,
                meta={
                    "source_key": self.source_key,
                    "provider": self.provider,
                    "bbox": bbox,
                },
            )
        raise LiveAccessNotImplementedError(self.source_key)


@dataclass(slots=True)
class CopernicusStacClient(CatalogClient):
    collection: str

    @property
    def actual_transport(self) -> str:
        if self.source_key == "sentinel3":
            return "not_implemented"
        return "planetary_computer_stac"

    @property
    def capability(self) -> str:
        if self.source_key == "sentinel3":
            return "fallback_only"
        return "working_now"

    def _search_items(self, bbox: tuple[float, float, float, float]) -> list:
        catalog = pystac_client.Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1",
            modifier=planetary_computer.sign_inplace,
        )
        search = catalog.search(
            collections=["sentinel-2-l2a"],  # Always Sentinel-2 for our demo map
            bbox=bbox,
            datetime="2023-06-01/2023-06-10",
            max_items=1,
        )
        return list(search.items())

    def load(
        self,
        bbox: tuple[float, float, float, float] = (0, 0, 0, 0),
        *,
        logger=None,
        run_id: str | None = None,
        mode: str = "offline",
    ) -> xr.Dataset:
        if self.source_key == "sentinel3":
            return super(CopernicusStacClient, self).load(
                bbox,
                logger=logger,
                run_id=run_id,
                mode=mode,
            )

        try:
            items = self._search_items(bbox)
        except Exception as exc:
            _log_probe_result(
                logger,
                dataset_probe_result(
                    provider=self.provider,
                    source_key=self.source_key,
                    status="live_failure",
                    detail="catalog probe failed",
                    capability=self.capability,
                    actual_transport=self.actual_transport,
                    run_id=run_id,
                    mode=mode,
                    meta={"bbox": bbox, "error": str(exc)},
                ),
            )
            raise

        if not items:
            status = "live_failure" if mode == "live_probe" else "live_failure_fallback"
            detail = (
                "catalog returned no items"
                if mode == "live_probe"
                else "catalog returned no items; fallback required"
            )
            _log_probe_result(
                logger,
                dataset_probe_result(
                    provider=self.provider,
                    source_key=self.source_key,
                    status=status,
                    detail=detail,
                    capability=self.capability,
                    actual_transport=self.actual_transport,
                    run_id=run_id,
                    mode=mode,
                    meta={"bbox": bbox, "item_count": 0},
                ),
            )
            if mode != "live_probe":
                _log_event(
                    logger,
                    "warning",
                    event="fallback.activated",
                    component="sources",
                    message=detail,
                    run_id=run_id,
                    mode=mode,
                    fallback_used=True,
                    meta={
                        "source_key": self.source_key,
                        "provider": self.provider,
                        "bbox": bbox,
                    },
                )
            return xr.Dataset()

        _log_probe_result(
            logger,
            dataset_probe_result(
                provider=self.provider,
                source_key=self.source_key,
                status="live_success",
                detail="catalog probe succeeded",
                capability=self.capability,
                actual_transport=self.actual_transport,
                run_id=run_id,
                mode=mode,
                meta={"bbox": bbox, "item_count": len(items)},
            ),
        )
        # Ensure we always return an xarray dataset even if empty
        return _ensure_dataset(
            odc.stac.load(items, bbox=bbox, resolution=30, chunks={})
        )


@dataclass(slots=True)
class OpenDataCubeClient(CatalogClient):
    product: str

    @property
    def actual_transport(self) -> str:
        return "planetary_computer_stac"

    @property
    def capability(self) -> str:
        return "needs_fix"

    def _search_items(self, bbox: tuple[float, float, float, float]) -> list:
        catalog = pystac_client.Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1",
            modifier=planetary_computer.sign_inplace,
        )
        search = catalog.search(
            collections=["landsat-c2-l2"],
            bbox=bbox,
            datetime="2023-06-01/2023-06-10",
            max_items=1,
        )
        return list(search.items())

    def load(
        self,
        bbox: tuple[float, float, float, float] = (0, 0, 0, 0),
        *,
        logger=None,
        run_id: str | None = None,
        mode: str = "offline",
    ) -> xr.Dataset:
        try:
            items = self._search_items(bbox)
        except Exception as exc:
            _log_probe_result(
                logger,
                dataset_probe_result(
                    provider=self.provider,
                    source_key=self.source_key,
                    status="live_failure",
                    detail="catalog probe failed",
                    capability=self.capability,
                    actual_transport=self.actual_transport,
                    run_id=run_id,
                    mode=mode,
                    meta={"bbox": bbox, "error": str(exc)},
                ),
            )
            raise

        if not items:
            status = "live_failure" if mode == "live_probe" else "live_failure_fallback"
            detail = (
                "catalog returned no items"
                if mode == "live_probe"
                else "catalog returned no items; fallback required"
            )
            _log_probe_result(
                logger,
                dataset_probe_result(
                    provider=self.provider,
                    source_key=self.source_key,
                    status=status,
                    detail=detail,
                    capability=self.capability,
                    actual_transport=self.actual_transport,
                    run_id=run_id,
                    mode=mode,
                    meta={"bbox": bbox, "item_count": 0},
                ),
            )
            if mode != "live_probe":
                _log_event(
                    logger,
                    "warning",
                    event="fallback.activated",
                    component="sources",
                    message=detail,
                    run_id=run_id,
                    mode=mode,
                    fallback_used=True,
                    meta={
                        "source_key": self.source_key,
                        "provider": self.provider,
                        "bbox": bbox,
                    },
                )
            return xr.Dataset()

        _log_probe_result(
            logger,
            dataset_probe_result(
                provider=self.provider,
                source_key=self.source_key,
                status="live_success",
                detail="catalog probe succeeded",
                capability=self.capability,
                actual_transport=self.actual_transport,
                run_id=run_id,
                mode=mode,
                meta={"bbox": bbox, "item_count": len(items)},
            ),
        )
        return _ensure_dataset(
            odc.stac.load(items, bbox=bbox, resolution=30, chunks={})
        )


def build_catalog_clients(
    catalogs: dict[str, str],
    *,
    logger=None,
    run_id: str | None = None,
    mode: str = "offline",
) -> dict[str, CatalogClient]:
    required_catalogs = {
        "sentinel2": "copernicus",
        "sentinel3": "copernicus",
        "landsat": "opendatacube",
    }
    provided_keys = set(catalogs)
    required_keys = set(required_catalogs)

    missing_keys = sorted(required_keys - provided_keys)
    if missing_keys:
        missing = ", ".join(missing_keys)
        _log_event(
            logger,
            "error",
            event="dataset.probe.failed",
            component="sources",
            message="catalog mapping is missing required sources",
            run_id=run_id,
            mode=mode,
            meta={"missing_keys": missing_keys},
        )
        raise ValueError(f"Missing required source keys: {missing}")

    extra_keys = sorted(provided_keys - required_keys)
    if extra_keys:
        extras = ", ".join(extra_keys)
        _log_event(
            logger,
            "error",
            event="dataset.probe.failed",
            component="sources",
            message="catalog mapping includes unknown sources",
            run_id=run_id,
            mode=mode,
            meta={"extra_keys": extra_keys},
        )
        raise ValueError(f"Unknown source keys: {extras}")

    clients: dict[str, CatalogClient] = {}
    for key, expected_provider in required_catalogs.items():
        value = catalogs[key]
        if value != expected_provider:
            _log_event(
                logger,
                "error",
                event="dataset.probe.failed",
                component="sources",
                message="catalog provider mapping is invalid",
                run_id=run_id,
                mode=mode,
                meta={
                    "source_key": key,
                    "provider": value,
                    "expected_provider": expected_provider,
                },
            )
            raise ValueError(
                f"Unsupported provider '{value}' for source '{key}'; expected '{expected_provider}'"
            )

        if value == "copernicus":
            clients[key] = CopernicusStacClient(
                source_key=key, provider=value, collection=key
            )
            continue

        if value == "opendatacube":
            clients[key] = OpenDataCubeClient(
                source_key=key, provider=value, product=key
            )
            continue

        _log_event(
            logger,
            "error",
            event="dataset.probe.failed",
            component="sources",
            message="catalog provider is unsupported",
            run_id=run_id,
            mode=mode,
            meta={"source_key": key, "provider": value},
        )
        raise ValueError(f"Unsupported catalog provider: {value}")

    return clients
