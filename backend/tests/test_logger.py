from pathlib import Path

from urbancanopy.logger import UrbancanopyLogger


def test_logger_writes_file_logs_and_event_store(tmp_path: Path) -> None:
    logger = UrbancanopyLogger.create(
        base_dir=tmp_path,
        timestamp="2026-03-22_12-30-00",
    )

    logger.info(
        event="fallback.activated",
        component="sources",
        message="using cached artifact",
        run_id="run-1",
        fallback_used=True,
        meta={"provider": "copernicus", "artifact": "priority_zones.geojson"},
    )

    assert (tmp_path / "2026-03-22_12-30-00_back.log").exists()
    recent = logger.store.list_recent_events(limit=1)
    assert recent[0]["event"] == "fallback.activated"
    assert recent[0]["fallbackUsed"] is True
