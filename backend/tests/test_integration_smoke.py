import pytest

from urbancanopy.config import load_run_config


@pytest.mark.integration
def test_multicity_demo_config_is_well_formed() -> None:
    from pathlib import Path
    
    config_path = Path(__file__).resolve().parent.parent / "configs" / "multicity-demo.yml"
    cfg = load_run_config(config_path)

    assert cfg.focus_city == "taipei"
    assert cfg.comparison_cities == ["taipei", "tokyo", "london", "new_york"]
