from dataclasses import dataclass


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

    def load(self, *_args: object, **_kwargs: object) -> None:
        raise LiveAccessNotImplementedError(self.source_key)


@dataclass(slots=True)
class CopernicusStacClient(CatalogClient):
    collection: str


@dataclass(slots=True)
class OpenDataCubeClient(CatalogClient):
    product: str


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
