from pathlib import Path

from urbancanopy.logging_utils import create_file_logger


def test_create_file_logger_writes_normal_debug_and_error_logs(tmp_path: Path) -> None:
    logger = create_file_logger(
        "back", base_dir=tmp_path, timestamp="2026-03-22_12-00-00"
    )

    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")

    info_log = tmp_path / "2026-03-22_12-00-00_back.log"
    debug_log = tmp_path / "2026-03-22_12-00-00_back_debug.log"
    error_log = tmp_path / "2026-03-22_12-00-00_back_error.log"

    assert info_log.exists()
    assert debug_log.exists()
    assert error_log.exists()

    assert info_log.read_text() == "info message\n"
    assert debug_log.read_text() == (
        "debug message\ninfo message\nwarning message\nerror message\n"
    )
    assert error_log.read_text() == "warning message\nerror message\n"


def test_create_file_logger_closes_replaced_handlers(tmp_path: Path) -> None:
    logger = create_file_logger(
        "back", base_dir=tmp_path, timestamp="2026-03-22_12-00-00"
    )
    original_handlers = list(logger.handlers)

    same_logger = create_file_logger(
        "back", base_dir=tmp_path, timestamp="2026-03-22_12-00-00"
    )

    assert same_logger is logger
    assert logger.handlers != original_handlers
    assert all(
        getattr(handler, "stream", None) is None for handler in original_handlers
    )
