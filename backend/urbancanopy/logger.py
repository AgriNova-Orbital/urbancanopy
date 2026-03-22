from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from typing import Any

from urbancanopy.event_store import EventStore
from urbancanopy.logging_schema import build_event
from urbancanopy.logging_utils import create_file_logger, serialize_event


@dataclass(slots=True)
class UrbancanopyLogger:
    logger: Logger
    store: EventStore

    @classmethod
    def create(
        cls,
        *,
        base_dir: Path | None = None,
        timestamp: str | None = None,
    ) -> "UrbancanopyLogger":
        resolved_base_dir = (
            base_dir
            if base_dir is not None
            else Path(__file__).resolve().parents[2] / "logs"
        )
        return cls(
            logger=create_file_logger(
                "back",
                base_dir=resolved_base_dir,
                timestamp=timestamp,
            ),
            store=EventStore.create(base_dir=resolved_base_dir, timestamp=timestamp),
        )

    def debug(self, **event_fields: Any) -> dict[str, Any]:
        return self._log(level="debug", **event_fields)

    def info(self, **event_fields: Any) -> dict[str, Any]:
        return self._log(level="info", **event_fields)

    def warning(self, **event_fields: Any) -> dict[str, Any]:
        return self._log(level="warning", **event_fields)

    def error(self, **event_fields: Any) -> dict[str, Any]:
        return self._log(level="error", **event_fields)

    def _log(self, *, level: str, **event_fields: Any) -> dict[str, Any]:
        event = build_event(level=level, **event_fields)
        getattr(self.logger, level)(serialize_event(event))
        self.store.append_event(event)
        return event
