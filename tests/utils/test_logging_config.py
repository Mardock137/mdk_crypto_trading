from src.utils.logging_config import configure_logging


def test_configure_logging_returns_named_logger() -> None:
    logger = configure_logging(logger_name="mdk_crypto_trading.tests", level="DEBUG")

    assert logger.name == "mdk_crypto_trading.tests"
    assert logger.level == 10
    assert logger.handlers


def test_configure_logging_is_idempotent() -> None:
    logger = configure_logging(logger_name="mdk_crypto_trading.idempotent")
    first_handler_count = len(logger.handlers)

    same_logger = configure_logging(logger_name="mdk_crypto_trading.idempotent")

    assert same_logger is logger
    assert len(same_logger.handlers) == first_handler_count

