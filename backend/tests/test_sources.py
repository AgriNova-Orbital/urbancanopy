from urbancanopy.sources import (
    CopernicusStacClient,
    LiveAccessNotImplementedError,
    OpenDataCubeClient,
    build_catalog_clients,
)

import pytest


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
        match="Live catalog access is not implemented for source 'sentinel2'",
    ):
        clients["sentinel2"].load()

    with pytest.raises(
        LiveAccessNotImplementedError,
        match="Live catalog access is not implemented for source 'landsat'",
    ):
        clients["landsat"].load()
