from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.runner import TradingRunner
from src.utils.config import AppSettings, TradingMode


def _make_settings(**overrides: Any) -> AppSettings:
    defaults: dict[str, Any] = {
        "trading_mode": TradingMode.DEMO,
        "kill_switch": False,
        "cycle_interval_seconds": 60,
        "openai_api_key": None,
        "gemini_api_key": None,
        "binance_api_key": None,
        "binance_secret_key": None,
        "binance_demo_api_key": None,
        "binance_demo_secret_key": None,
        "binance_demo_base_url": None,
        "log_level": "INFO",
    }
    defaults.update(overrides)
    return AppSettings(**defaults)


def _make_runner(
    settings: AppSettings | None = None,
    workflow: MagicMock | None = None,
    event_logger: MagicMock | None = None,
) -> TradingRunner:
    return TradingRunner(
        workflow=workflow or MagicMock(),
        event_logger=event_logger or MagicMock(),
        logger=logging.getLogger("mdk_crypto_trading.test_runner"),
        settings=settings or _make_settings(),
        symbol="BTCUSDC",
    )


# ---------- Ciclo singolo ----------


@patch("src.core.runner.time.sleep", side_effect=KeyboardInterrupt)
def test_run_sleeps_even_after_cycle_error(mock_sleep: MagicMock) -> None:
    """Anche se il ciclo fallisce, il runner dorme prima di riprovare."""
    runner = _make_runner()

    runner.run()

    mock_sleep.assert_called_once_with(60)


# ---------- Gestione errore ----------


@patch("src.core.runner.time.sleep", side_effect=KeyboardInterrupt)
def test_run_logs_error_on_exception(mock_sleep: MagicMock) -> None:
    """Se il ciclo fallisce, il runner logga l'errore e non crasha."""
    mock_event_logger = MagicMock()
    runner = _make_runner(event_logger=mock_event_logger)

    # _build_cycle_input solleva NotImplementedError → viene gestita
    runner.run()

    mock_event_logger.log_error.assert_called_once()
    call_kwargs = mock_event_logger.log_error.call_args.kwargs
    assert call_kwargs["symbol"] == "BTCUSDC"
    assert call_kwargs["trading_mode"] == "DEMO"
    assert "NotImplementedError" in call_kwargs["error"] or "_build_cycle_input" in call_kwargs["error"]


# ---------- Kill switch ----------


@patch("src.core.runner.time.sleep", side_effect=KeyboardInterrupt)
def test_run_logs_warning_when_kill_switch_active(
    mock_sleep: MagicMock, caplog: pytest.LogCaptureFixture,
) -> None:
    """Se kill_switch è True, il runner logga un avviso all'avvio."""
    settings = _make_settings(kill_switch=True)
    runner = _make_runner(settings=settings)

    with caplog.at_level(logging.WARNING):
        runner.run()

    assert any("kill switch" in msg.lower() for msg in caplog.messages)


# ---------- _build_cycle_input ----------


def test_build_cycle_input_raises_not_implemented() -> None:
    """_build_cycle_input deve sollevare NotImplementedError (stub Fase 5)."""
    runner = _make_runner()

    with pytest.raises(NotImplementedError):
        runner._build_cycle_input()
