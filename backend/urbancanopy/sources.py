from dataclasses import dataclass


@dataclass(slots=True)
class CatalogClient:
    provider: str

    @property
    def name(self) -> str:
        return self.provider


@dataclass(slots=True)
class CopernicusStacClient(CatalogClient):
    collection: str

    def search_items(self, *_args: object, **_kwargs: object) -> None:
        raise NotImplementedError

    def load_metadata(self, *_args: object, **_kwargs: object) -> None:
        raise NotImplementedError


@dataclass(slots=True)
class OpenDataCubeClient(CatalogClient):
    product: str

    def discover_product(self, *_args: object, **_kwargs: object) -> None:
        raise NotImplementedError

    def load_items(self, *_args: object, **_kwargs: object) -> None:
        raise NotImplementedError


def build_catalog_clients(catalogs: dict[str, str]) -> dict[str, CatalogClient]:
    clients: dict[str, CatalogClient] = {}
    for key, value in catalogs.items():
        if value == "copernicus":
            clients[key] = CopernicusStacClient(provider=value, collection=key)
            continue

        if value == "opendatacube":
            clients[key] = OpenDataCubeClient(provider=value, product=key)
            continue

        raise ValueError(f"Unsupported catalog provider: {value}")

    return clients
