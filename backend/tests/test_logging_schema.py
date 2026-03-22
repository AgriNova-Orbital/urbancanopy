from urbancanopy.logging_schema import build_event


def test_build_event_creates_structured_event_envelope() -> None:
    event = build_event(
        level="info",
        event="pipeline.started",
        component="cli",
        message="pipeline starting",
        run_id="run-123",
        mode="offline_demo",
        fallback_used=False,
        meta={"focus_city": "taipei"},
    )

    assert event["level"] == "info"
    assert event["event"] == "pipeline.started"
    assert event["component"] == "cli"
    assert event["runId"] == "run-123"
    assert event["fallbackUsed"] is False
    assert event["meta"]["focus_city"] == "taipei"
    assert "ts" in event
