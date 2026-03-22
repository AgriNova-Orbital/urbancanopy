from pathlib import Path

from urbancanopy.event_store import EventStore


def test_event_store_persists_and_reads_events(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "events.db")
    store.initialize()
    store.append_event(
        {
            "ts": "2026-03-22T12:00:00Z",
            "level": "info",
            "event": "pipeline.started",
            "component": "cli",
            "message": "starting",
            "runId": "run-1",
            "jobId": None,
            "mode": "offline_demo",
            "online": False,
            "fallbackUsed": False,
            "meta": {"focus_city": "taipei"},
        }
    )

    events = store.list_recent_events(limit=10)

    assert len(events) == 1
    assert events[0]["event"] == "pipeline.started"
    assert events[0]["meta"]["focus_city"] == "taipei"
