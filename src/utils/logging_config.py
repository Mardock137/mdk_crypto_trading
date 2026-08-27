from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_LOG_FILE_NAME = "mdk_crypto_trading.log"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 5
_GENAI_MODELS_LOGGER = "google_genai.models"
_AFC_WARNING_MARKER = "Direct use of automatic function calling"


class _SuppressGenaiAfcWarning(logging.Filter):
    """Scarta solo il warning AFC di google-genai su Models.generate_content."""

    def filter(self, record: logging.LogRecord) -> bool:
        return _AFC_WARNING_MARKER not in record.getMessage()


def _install_genai_afc_filter() -> None:
    genai_logger = logging.getLogger(_GENAI_MODELS_LOGGER)
    if any(isinstance(item, _SuppressGenaiAfcWarning) for item in genai_logger.filters):
        return
    genai_logger.addFilter(_SuppressGenaiAfcWarning())


def configure_logging(
    logger_name: str = "mdk_crypto_trading",
    level: str = "INFO",
    log_dir: str | Path = "logs",
) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(level.upper())
    _install_genai_afc_filter()

    if logger.handlers:
        return logger

    formatter = logging.Formatter(_LOG_FORMAT)

    # Handler console (Rich se disponibile, altrimenti StreamHandler)
    console_handler = _build_console_handler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler file con rotazione automatica
    file_handler = _build_file_handler(log_dir, formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def _build_console_handler() -> logging.Handler:
    try:
        from rich.logging import RichHandler

        return RichHandler(rich_tracebacks=False, show_path=False)
    except ImportError:
        return logging.StreamHandler()


def _build_file_handler(
    log_dir: str | Path,
    formatter: logging.Formatter,
) -> RotatingFileHandler:
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        filename=log_path / _LOG_FILE_NAME,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    return handler
