from pathlib import Path

from urbancanopy.cities import get_city_fixture_path, build_comparison_zones
from urbancanopy.comparison import summarize_city_heat_gap
from urbancanopy.config import load_run_config
from urbancanopy.exports import (
    export_city_comparison,
    export_city_signature,
    export_park_cooling,
    export_priority_zones,
)
from urbancanopy.modeling import build_city_signature_table
from urbancanopy.parks import pci_summary
from urbancanopy.scoring import priority_score
from urbancanopy.sources import build_catalog_clients
from urbancanopy.vectorize import vectorize_priority_cells


def execute_pipeline(*, config_path: Path, output_dir: Path) -> dict[str, Path]:
    # 1. Config & Providers
    cfg = load_run_config(config_path)
    clients = build_catalog_clients(cfg.catalogs)

    # 2. Focus City & Comparison Registry
    focus_city_path = get_city_fixture_path(cfg.focus_city)
    comparison_paths = [get_city_fixture_path(c) for c in cfg.comparison_cities]

    # At this point, live data access is required to compute metrics,
    # generate datasets and export them.
    # The clients will raise a LiveAccessNotImplementedError
    clients["sentinel3"].load()

    # The rest of the pipeline composing these modules would go here:
    # summarize_city_heat_gap(...)
    # build_city_signature_table(...)
    # priority_score(...)
    # vectorize_priority_cells(...)
    # pci_summary(...)
    #
    # Then export the results:
    # export_priority_zones(zones, output_dir / "priority_zones.geojson")
    # export_city_comparison(comparison, output_dir / "city_comparison.csv")
    # export_city_signature(signature, output_dir / "city_signature.csv")
    # export_park_cooling(parks, output_dir / "park_cooling.csv")

    return {
        "priority_geojson": output_dir / "priority_zones.geojson",
        "city_comparison_csv": output_dir / "city_comparison.csv",
        "city_signature_csv": output_dir / "city_signature.csv",
        "park_cooling_csv": output_dir / "park_cooling.csv",
    }


def run_pipeline(*, config_path: Path, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    return execute_pipeline(config_path=config_path, output_dir=output_dir)


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Run Urban Cooling Pipeline")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    try:
        run_pipeline(config_path=args.config, output_dir=args.output_dir)
        print("Pipeline completed successfully.")
    except Exception as e:
        print(f"Pipeline error: {e}")
        sys.exit(1)

def main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Run Urban Cooling Pipeline")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    try:
        run_pipeline(config_path=args.config, output_dir=args.output_dir)
        print("Pipeline completed successfully.")
    except Exception as e:
        print(f"Pipeline error: {e}")
        sys.exit(1)
