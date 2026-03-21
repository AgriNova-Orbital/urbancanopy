from pathlib import Path

import pytest

from urbancanopy.config import load_run_config


@pytest.mark.integration
def test_multicity_demo_config_is_well_formed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(Path(__file__).resolve().parent.parent)

    cfg = load_run_config("configs/multicity-demo.yml")

    assert cfg.focus_city == "taipei"
    assert cfg.comparison_cities == ["taipei", "tokyo", "london", "new_york"]
