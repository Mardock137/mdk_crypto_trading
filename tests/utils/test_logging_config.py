from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.utils.logging_config import (
    _SuppressGenaiAfcWarning,
    configure_logging,
)


def _make_record(message: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="google_genai.models",
        level=logging.WARNING,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )


def test_configure_logging_returns_named_logger(tmp_path: Path) -> None:
    logger = configure_logging(
        logger_name="mdk_crypto_trading.test_named",
        level="DEBUG",
        log_dir=tmp_path,
    )

    assert logger.name == "mdk_crypto_trading.test_named"
    assert logger.level == logging.DEBUG
    assert logger.handlers


def test_configure_logging_is_idempotent(tmp_path: Path) -> None:
    logger = configure_logging(
        logger_name="mdk_crypto_trading.test_idempotent",
        log_dir=tmp_path,
    )
    first_handler_count = len(logger.handlers)

    same_logger = configure_logging(
        logger_name="mdk_crypto_trading.test_idempotent",
        log_dir=tmp_path,
    )

    assert same_logger is logger
    assert len(same_logger.handlers) == first_handler_count


def test_configure_logging_has_two_handlers(tmp_path: Path) -> None:
    """Il logger deve avere esattamente due handler: console + file."""
    logger = configure_logging(
        logger_name="mdk_crypto_trading.test_two_handlers",
        log_dir=tmp_path,
    )

    assert len(logger.handlers) == 2

    handler_types = {type(h) for h in logger.handlers}
    assert RotatingFileHandler in handler_types


def test_configure_logging_creates_log_file(tmp_path: Path) -> None:
    """Il file di log deve essere creato nella cartella specificata."""
    logger = configure_logging(
        logger_name="mdk_crypto_trading.test_file_creation",
        log_dir=tmp_path,
    )

    logger.info("Messaggio di test")

    log_file = tmp_path / "mdk_crypto_trading.log"
    assert log_file.exists()
    assert "Messaggio di test" in log_file.read_text(encoding="utf-8")


def test_afc_warning_filter_drops_exact_message() -> None:
    filt = _SuppressGenaiAfcWarning()
    record = _make_record(
        "Direct use of automatic function calling (AFC) in Models.generate_content "
        "is not recommended."
    )

    assert filt.filter(record) is False


def test_afc_warning_filter_keeps_other_messages() -> None:
    filt = _SuppressGenaiAfcWarning()
    record = _make_record("Unrelated google-genai warning that should still appear.")

    assert filt.filter(record) is True


def test_configure_logging_installs_genai_afc_filter_once(tmp_path: Path) -> None:
    configure_logging(
        logger_name="mdk_crypto_trading.test_genai_afc_filter",
        log_dir=tmp_path,
    )
    configure_logging(
        logger_name="mdk_crypto_trading.test_genai_afc_filter",
        log_dir=tmp_path,
    )

    genai_logger = logging.getLogger("google_genai.models")
    afc_filters = [
        item
        for item in genai_logger.filters
        if isinstance(item, _SuppressGenaiAfcWarning)
    ]
    assert len(afc_filters) == 1
