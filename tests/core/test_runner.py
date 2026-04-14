from __future__ import annotations

import logging
import signal
import threading
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.contracts import (
    ExecutionReport,
    ExecutionStatus,
    OrderType,
    TradeAction,
    TradeProposal,
    TradeProposalDetails,
)
from src.core.runner import TradingRunner
from src.utils.config import AppSettings, TradingMode
from src.utils.memory_manager import MemoryManager
from src.utils.telegram_notifier import TelegramNotifier

_MOCK_TRADING_CONFIG = {"min_order_usdc": 10.0}


def _make_settings(**overrides: Any) -> AppSettings:
    defaults: dict[str, Any] = {
        "trading_mode": TradingMode.DEMO,
        "kill_switch": False,
        "cycle_interval_seconds": 60,
        "openai_api_key": None,
        "gemini_api_key": None,
        "claude_api_key": None,
        "binance_api_key": None,
        "binance_secret_key": None,
        "binance_demo_api_key": None,
        "binance_demo_secret_key": None,
        "binance_demo_base_url": None,
        "log_level": "INFO",
        "telegram_bot_token": None,
        "telegram_chat_id": None,
    }
    defaults.update(overrides)
    return AppSettings(**defaults)


def _make_runner(
    settings: AppSettings | None = None,
    workflow: MagicMock | None = None,
    event_logger: MagicMock | None = None,
    exchange_client: MagicMock | None = None,
    memory_manager: MemoryManager | None = None,
    telegram_notifier: TelegramNotifier | None = None,
) -> TradingRunner:
    with patch("src.core.runner.load_trading_config", return_value=_MOCK_TRADING_CONFIG):
        return TradingRunner(
            workflow=workflow or MagicMock(),
            event_logger=event_logger or MagicMock(),
            logger=logging.getLogger("mdk_crypto_trading.test_runner"),
            settings=settings or _make_settings(),
            symbol="BTCUSDC",
            exchange_client=exchange_client or MagicMock(),
            memory_manager=memory_manager or MagicMock(spec=MemoryManager),
            telegram_notifier=telegram_notifier,
        )


# ---------- Ciclo singolo ----------


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_run_sleeps_even_after_cycle_error(mock_wait: MagicMock) -> None:
    """Anche se il ciclo fallisce, il runner attende prima di riprovare."""
    runner = _make_runner()

    runner.run()

    mock_wait.assert_called_once_with(60)


# ---------- Gestione errore ----------


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_run_logs_error_on_exception(mock_wait: MagicMock) -> None:
    """Se il ciclo fallisce, il runner logga l'errore e non crasha."""
    mock_event_logger = MagicMock()
    mock_workflow = MagicMock()
    mock_workflow.run_cycle.side_effect = RuntimeError("errore di test")
    runner = _make_runner(event_logger=mock_event_logger, workflow=mock_workflow)

    runner.run()

    mock_event_logger.log_error.assert_called_once()
    call_kwargs = mock_event_logger.log_error.call_args.kwargs
    assert call_kwargs["symbol"] == "BTCUSDC"
    assert call_kwargs["trading_mode"] == "DEMO"
    assert "errore di test" in call_kwargs["error"]


# ---------- Kill switch ----------


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_run_logs_warning_when_kill_switch_active(
    mock_wait: MagicMock, caplog: pytest.LogCaptureFixture,
) -> None:
    """Se kill_switch è True, il runner logga un avviso all'avvio."""
    settings = _make_settings(kill_switch=True)
    runner = _make_runner(settings=settings)

    with caplog.at_level(logging.WARNING):
        runner.run()

    assert any("kill switch" in msg.lower() for msg in caplog.messages)


# ---------- _build_cycle_input ----------


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_build_cycle_input_calls_exchange_client(mock_wait: MagicMock) -> None:
    """_build_cycle_input deve chiamare get_market_snapshot e get_portfolio_state."""
    mock_exchange = MagicMock()
    mock_workflow = MagicMock()
    runner = _make_runner(exchange_client=mock_exchange, workflow=mock_workflow)

    runner.run()

    mock_exchange.get_market_snapshot.assert_called_with("BTCUSDC")
    mock_exchange.get_portfolio_state.assert_called_with("BTCUSDC")


# ---------- Notifiche Telegram ----------


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_run_sends_startup_notification(mock_wait: MagicMock) -> None:
    """Il runner deve inviare una notifica di avvio con il nuovo stile."""
    mock_notifier = MagicMock(spec=TelegramNotifier)
    runner = _make_runner(telegram_notifier=mock_notifier)

    runner.run()

    assert mock_notifier.send_message.call_count >= 1
    first_call_text: str = mock_notifier.send_message.call_args_list[0].args[0]
    assert "STARTED" in first_call_text


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_run_sends_stop_notification(mock_wait: MagicMock) -> None:
    """Il runner deve inviare una notifica di stop su KeyboardInterrupt."""
    mock_notifier = MagicMock(spec=TelegramNotifier)
    runner = _make_runner(telegram_notifier=mock_notifier)

    runner.run()

    texts = [call.args[0] for call in mock_notifier.send_message.call_args_list]
    assert any("STOPPED" in t for t in texts)


@patch("src.core.runner.signal.signal")
@patch("src.core.runner.threading.Event.wait")
def test_run_sends_stop_notification_on_sigterm(
    mock_wait: MagicMock, mock_signal: MagicMock
) -> None:
    """Il runner deve inviare la notifica di stop anche quando viene ricevuto SIGTERM."""
    mock_notifier = MagicMock(spec=TelegramNotifier)
    runner = _make_runner(telegram_notifier=mock_notifier)

    captured_handlers: dict[int, Any] = {}

    def _capture_signal(signum: int, handler: Any) -> None:
        captured_handlers[signum] = handler

    mock_signal.side_effect = _capture_signal
    mock_wait.side_effect = lambda _: captured_handlers[signal.SIGTERM](
        signal.SIGTERM, None
    )

    runner.run()

    texts = [call.args[0] for call in mock_notifier.send_message.call_args_list]
    assert any("STOPPED" in t for t in texts)


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_run_sends_error_notification_on_exception(mock_wait: MagicMock) -> None:
    """Su errore nel ciclo, il runner deve inviare una notifica Telegram."""
    mock_notifier = MagicMock(spec=TelegramNotifier)
    mock_workflow = MagicMock()
    mock_workflow.run_cycle.side_effect = RuntimeError("boom")
    runner = _make_runner(workflow=mock_workflow, telegram_notifier=mock_notifier)

    runner.run()

    texts = [call.args[0] for call in mock_notifier.send_message.call_args_list]
    assert any("ERROR" in t and "boom" in t for t in texts)


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_run_sends_order_notification_when_executed(mock_wait: MagicMock) -> None:
    """Quando un ordine è EXECUTED, il runner deve inviare una notifica."""
    mock_notifier = MagicMock(spec=TelegramNotifier)
    mock_workflow = MagicMock()
    mock_result = mock_workflow.run_cycle.return_value
    mock_result.execution_report.was_executed = True
    mock_result.execution_report.executed_action = TradeAction.BUY
    mock_result.execution_report.order_type = OrderType.MARKET
    mock_result.execution_report.execution_status = ExecutionStatus.EXECUTED
    mock_result.execution_report.execution_details = {
        "cummulativeQuoteQty": "27.43",
        "executedQty": "0.0004",
    }
    mock_result.trade_proposal = TradeProposal(
        action=TradeAction.BUY,
        order_type=OrderType.MARKET,
        confidence=0.63,
        reason="test",
        details=TradeProposalDetails(quantity=0.0004),
    )
    runner = _make_runner(workflow=mock_workflow, telegram_notifier=mock_notifier)

    runner.run()

    texts = [call.args[0] for call in mock_notifier.send_message.call_args_list]
    assert any("EXECUTED" in t for t in texts)


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_run_does_not_send_order_notification_when_not_executed(
    mock_wait: MagicMock,
) -> None:
    """Quando l'ordine NON è eseguito, non deve arrivare notifica di ordine."""
    mock_notifier = MagicMock(spec=TelegramNotifier)
    mock_workflow = MagicMock()
    mock_result = mock_workflow.run_cycle.return_value
    mock_result.execution_report.was_executed = False
    runner = _make_runner(workflow=mock_workflow, telegram_notifier=mock_notifier)

    runner.run()

    texts = [call.args[0] for call in mock_notifier.send_message.call_args_list]
    assert not any("ESEGUITO" in t for t in texts)
