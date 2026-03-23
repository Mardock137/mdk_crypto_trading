from __future__ import annotations

import logging


def configure_logging(
    logger_name: str = "mdk_crypto_trading",
    level: str = "INFO",
) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(level.upper())

    if logger.handlers:
        return logger

    handler = _build_handler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False
    return logger


def _build_handler() -> logging.Handler:
    try:
        from rich.logging import RichHandler

        return RichHandler(rich_tracebacks=True, show_path=False)
    except ImportError:
        return logging.StreamHandler()

