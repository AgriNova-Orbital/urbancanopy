from datetime import datetime, timezone


def build_event(
    *,
    level: str,
    event: str,
    component: str,
    message: str,
    run_id: str | None = None,
    job_id: str | None = None,
    mode: str = "offline",
    online: bool | None = None,
    fallback_used: bool = False,
    meta: dict | None = None,
) -> dict:
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event": event,
        "component": component,
        "message": message,
        "runId": run_id,
        "jobId": job_id,
        "mode": mode,
        "online": online,
        "fallbackUsed": fallback_used,
        "meta": dict(meta) if meta is not None else {},
    }
