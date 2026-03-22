from inspect import signature
from pathlib import Path

import pytest

from urbancanopy.logger import UrbancanopyLogger
from urbancanopy.sources import (
    CatalogClient,
    CopernicusStacClient,
    LiveAccessNotImplementedError,
    OpenDataCubeClient,
    build_catalog_clients,
)


def test_build_catalog_clients_uses_copernicus_for_sentinel_and_odc_for_landsat() -> (
    None
):
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


def test_build_catalog_clients_returns_typed_adapters_for_supported_catalogs() -> None:
    clients = build_catalog_clients(
        {
            "sentinel2": "copernicus",
            "sentinel3": "copernicus",
            "landsat": "opendatacube",
        }
    )

    assert isinstance(clients["sentinel2"], CopernicusStacClient)
    assert clients["sentinel2"].provider == "copernicus"
    assert clients["sentinel2"].collection == "sentinel2"

    assert isinstance(clients["sentinel3"], CopernicusStacClient)
    assert clients["sentinel3"].provider == "copernicus"
    assert clients["sentinel3"].collection == "sentinel3"

    assert isinstance(clients["landsat"], OpenDataCubeClient)
    assert clients["landsat"].provider == "opendatacube"
    assert clients["landsat"].product == "landsat"


@pytest.mark.parametrize(
    ("catalogs", "message"),
    [
        (
            {"sentinel2": "copernicus", "landsat": "opendatacube"},
            "Missing required source keys: sentinel3",
        ),
        (
            {
                "sentinel2": "copernicus",
                "sentinel3": "copernicus",
                "landsat": "opendatacube",
                "modis": "copernicus",
            },
            "Unknown source keys: modis",
        ),
        (
            {
                "sentinel2": "opendatacube",
                "sentinel3": "copernicus",
                "landsat": "opendatacube",
            },
            "Unsupported provider 'opendatacube' for source 'sentinel2'; expected 'copernicus'",
        ),
    ],
)
def test_build_catalog_clients_rejects_invalid_catalog_mappings(
    catalogs: dict[str, str], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        build_catalog_clients(catalogs)


def test_adapters_expose_offline_safe_load_contract() -> None:
    clients = build_catalog_clients(
        {
            "sentinel2": "copernicus",
            "sentinel3": "copernicus",
            "landsat": "opendatacube",
        }
    )

    with pytest.raises(
        LiveAccessNotImplementedError,
        match="Live catalog access is not implemented for source 'sentinel3'",
    ):
        clients["sentinel3"].load()


def test_live_catalog_clients_load_dataarray_when_implemented(monkeypatch) -> None:
    import xarray as xr
    from urbancanopy.sources import CopernicusStacClient, OpenDataCubeClient

    clients = build_catalog_clients(
        {
            "sentinel2": "copernicus",
            "sentinel3": "copernicus",
            "landsat": "opendatacube",
        }
    )

    monkeypatch.setattr(
        "pystac_client.Client.open", lambda *args, **kwargs: "mock_catalog"
    )
    monkeypatch.setattr(
        CopernicusStacClient,
        "_search_items",
        lambda self, *args, **kwargs: ["mock_item"],
    )
    monkeypatch.setattr(
        OpenDataCubeClient, "_search_items", lambda self, *args, **kwargs: ["mock_item"]
    )
    monkeypatch.setattr(
        "odc.stac.load", lambda *args, **kwargs: xr.DataArray([1], dims=["x"])
    )

    result_s2 = clients["sentinel2"].load(bbox=(121.5, 25.0, 121.6, 25.1))
    assert isinstance(result_s2, xr.DataArray)

    result_landsat = clients["landsat"].load(bbox=(121.5, 25.0, 121.6, 25.1))
    assert isinstance(result_landsat, xr.DataArray)


def test_build_catalog_clients_logs_probe_failures(tmp_path: Path) -> None:
    logger = UrbancanopyLogger.create(
        base_dir=tmp_path,
        timestamp="2026-03-22_12-46-00",
    )

    with pytest.raises(ValueError, match="Missing required source keys: sentinel3"):
        build_catalog_clients(
            {
                "sentinel2": "copernicus",
                "landsat": "opendatacube",
            },
            logger=logger,
            run_id="run-1",
            mode="offline_demo",
        )

    recent = logger.store.list_recent_events(limit=1)
    assert recent[0]["event"] == "dataset.probe.failed"
    assert recent[0]["meta"]["missing_keys"] == ["sentinel3"]


def test_catalog_client_load_contract_allows_future_data_return_values() -> None:
    import xarray as xr

    assert signature(CatalogClient.load).return_annotation is xr.DataArray
