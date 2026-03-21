from urbancanopy.sources import (
    CopernicusStacClient,
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
