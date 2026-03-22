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
from typing import Literal


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
    logger.handlers.clear()
    logger.setLevel(DEBUG)
    logger.propagate = False

    formatter = Formatter("%(message)s")

    info_handler = FileHandler(log_dir / f"{stamp}_{side}.log")
    info_handler.setLevel(INFO)
    info_handler.addFilter(ExactLevelFilter(INFO))
    info_handler.setFormatter(formatter)

    debug_handler = FileHandler(log_dir / f"{stamp}_{side}_debug.log")
    debug_handler.setLevel(DEBUG)
    debug_handler.setFormatter(formatter)

    error_handler = FileHandler(log_dir / f"{stamp}_{side}_error.log")
    error_handler.setLevel(WARNING)
    error_handler.setFormatter(formatter)

    logger.addHandler(info_handler)
    logger.addHandler(debug_handler)
    logger.addHandler(error_handler)
    return logger
