import json
from os import PathLike
from datetime import datetime
from logging import (
    DEBUG,
    INFO,
    WARNING,
    FileHandler,
    Filter,
    Formatter,
    Logger,
    getLogger,
)
from pathlib import Path
from typing import Any, Literal


class ExactLevelFilter(Filter):
    def __init__(self, level: int) -> None:
        super().__init__()
        self.level = level

    def filter(self, record) -> bool:
        return record.levelno == self.level


def create_file_logger(
    side: Literal["front", "back"],
    *,
    base_dir: Path | None = None,
    timestamp: str | None = None,
) -> Logger:
    log_dir = (
        base_dir
        if base_dir is not None
        else Path(__file__).resolve().parents[2] / "logs"
    )
    log_dir.mkdir(parents=True, exist_ok=True)

    stamp = (
        timestamp
        if timestamp is not None
        else datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    )
    logger = getLogger(f"urbancanopy.{side}.{stamp}.{log_dir}")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    logger.setLevel(DEBUG)
    logger.propagate = False

    formatter = Formatter("%(message)s")

    info_handler = FileHandler(log_dir / f"{stamp}_{side}.log", encoding="utf-8")
    info_handler.setLevel(INFO)
    info_handler.addFilter(ExactLevelFilter(INFO))
    info_handler.setFormatter(formatter)

    debug_handler = FileHandler(log_dir / f"{stamp}_{side}_debug.log", encoding="utf-8")
    debug_handler.setLevel(DEBUG)
    debug_handler.setFormatter(formatter)

    error_handler = FileHandler(log_dir / f"{stamp}_{side}_error.log", encoding="utf-8")
    error_handler.setLevel(WARNING)
    error_handler.setFormatter(formatter)

    logger.addHandler(info_handler)
    logger.addHandler(debug_handler)
    logger.addHandler(error_handler)
    return logger


def serialize_event(event: dict[str, Any]) -> str:
    return json.dumps(event, sort_keys=True, default=_json_default)


def _json_default(value: Any) -> str:
    if isinstance(value, PathLike):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
