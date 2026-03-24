from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.utils.logging_config import configure_logging


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
