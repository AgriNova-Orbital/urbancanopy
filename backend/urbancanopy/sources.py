from dataclasses import dataclass
import pystac_client
import planetary_computer
import odc.stac
import xarray as xr

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

    def load(self, bbox: tuple[float, float, float, float] = (0, 0, 0, 0)) -> xr.DataArray:
        raise LiveAccessNotImplementedError(self.source_key)

@dataclass(slots=True)
class CopernicusStacClient(CatalogClient):
    collection: str

    def _search_items(self, bbox: tuple[float, float, float, float]) -> list:
        catalog = pystac_client.Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1",
            modifier=planetary_computer.sign_inplace,
        )
        search = catalog.search(
            collections=["sentinel-2-l2a"], # Always Sentinel-2 for our demo map
            bbox=bbox,
            datetime="2023-06-01/2023-06-10",
            max_items=1,
        )
        return list(search.items())

    def load(self, bbox: tuple[float, float, float, float] = (0, 0, 0, 0)) -> xr.DataArray:
        if self.source_key == "sentinel3":
            raise LiveAccessNotImplementedError(self.source_key)

        items = self._search_items(bbox)
        if not items:
            return xr.DataArray()
        # Ensure we always return an xarray dataarray even if empty
        return odc.stac.load(items, bbox=bbox, resolution=30, chunks={})

@dataclass(slots=True)
class OpenDataCubeClient(CatalogClient):
    product: str

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

    def load(self, bbox: tuple[float, float, float, float] = (0, 0, 0, 0)) -> xr.DataArray:
        items = self._search_items(bbox)
        if not items:
            return xr.DataArray()
        return odc.stac.load(items, bbox=bbox, resolution=30, chunks={})

def build_catalog_clients(catalogs: dict[str, str]) -> dict[str, CatalogClient]:
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
        raise ValueError(f"Missing required source keys: {missing}")

    extra_keys = sorted(provided_keys - required_keys)
    if extra_keys:
        extras = ", ".join(extra_keys)
        raise ValueError(f"Unknown source keys: {extras}")

    clients: dict[str, CatalogClient] = {}
    for key, expected_provider in required_catalogs.items():
        value = catalogs[key]
        if value != expected_provider:
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

        raise ValueError(f"Unsupported catalog provider: {value}")

    return clients
