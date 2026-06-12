from __future__ import annotations

import logging
import signal
import threading
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.contracts import (
    CycleContextSnapshot,
    CycleSkipConfig,
    ExecutionStatus,
    MandateAdherence,
    MarketAnalysis,
    MarketBias,
    MarketDataSnapshot,
    OrderType,
    PerformanceReview,
    PerformanceStats,
    PortfolioState,
    RiskAssessment,
    RiskDecision,
    SuggestedAction,
    TradeAction,
    TradeProposal,
    TradeProposalDetails,
)
from src.core.exceptions import (
    CycleExecutionError,
    ExchangeError,
    LlmError,
    MdkTradingError,
)
from src.core.circuit_breaker import CircuitBreaker
from src.core.runner import TradingRunner, _classify_error
from src.utils.config import AppSettings, TradingMode
from src.utils.memory_manager import MemoryManager
from src.utils.telegram_notifier import TelegramNotifier

_MOCK_TRADING_CONFIG = {
    "min_order_usdc": 10.0,
    "mandate": {
        "max_drawdown_pct": 15.0,
        "horizon": "Intraday to swing",
        "max_position_pct": 70.0,
    },
}


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


_DEFAULT_DISABLED_SKIP_CONFIG = CycleSkipConfig(
    enabled=False,
    max_consecutive_skips=4,
    price_delta_pct=0.5,
    rsi_delta=2.0,
    macd_sign_must_match=True,
    require_no_order_events=True,
    require_previous_action_hold=True,
)


def _make_runner(
    settings: AppSettings | None = None,
    workflow: MagicMock | None = None,
    event_logger: MagicMock | None = None,
    exchange_client: MagicMock | None = None,
    memory_manager: MemoryManager | None = None,
    performance_reviewer: MagicMock | None = None,
    telegram_notifier: TelegramNotifier | None = None,
    performance_reports_dir: Path | None = None,
    cycle_skip_config: CycleSkipConfig | None = None,
    circuit_breaker: CircuitBreaker | None = None,
) -> TradingRunner:
    with patch(
        "src.core.runner.load_trading_config", return_value=_MOCK_TRADING_CONFIG,
    ), patch(
        "src.core.runner.load_cycle_skip_config",
        return_value=cycle_skip_config or _DEFAULT_DISABLED_SKIP_CONFIG,
    ):
        return TradingRunner(
            workflow=workflow or MagicMock(),
            event_logger=event_logger or MagicMock(),
            logger=logging.getLogger("mdk_crypto_trading.test_runner"),
            settings=settings or _make_settings(),
            symbol="BTCUSDC",
            exchange_client=exchange_client or MagicMock(),
            memory_manager=memory_manager or MagicMock(spec=MemoryManager),
            performance_reviewer=performance_reviewer or MagicMock(),
            telegram_notifier=telegram_notifier,
            performance_reports_dir=(
                performance_reports_dir
                if performance_reports_dir is not None
                else Path("data/performance_reports")
            ),
            circuit_breaker=circuit_breaker,
        )


# ---------- Heartbeat ----------


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_touch_heartbeat_writes_file(mock_wait: MagicMock, tmp_path: Path) -> None:
    """_touch_heartbeat deve scrivere un file con timestamp ISO nella cartella data/."""
    heartbeat_path = tmp_path / "heartbeat"
    runner = _make_runner()

    with patch("src.core.runner._HEARTBEAT_PATH", heartbeat_path):
        runner._touch_heartbeat()

    assert heartbeat_path.exists()
    content = heartbeat_path.read_text(encoding="utf-8")
    assert "T" in content  # formato ISO 8601


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_touch_heartbeat_called_each_cycle(mock_wait: MagicMock, tmp_path: Path) -> None:
    """_touch_heartbeat deve essere chiamato ad ogni ciclo."""
    runner = _make_runner()

    with patch.object(runner, "_touch_heartbeat") as mock_touch:
        runner.run()

    mock_touch.assert_called_once()


# ---------- Ciclo singolo ----------


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_run_sleeps_even_after_cycle_error(mock_wait: MagicMock) -> None:
    """Anche se il ciclo fallisce, il runner attende prima di riprovare."""
    runner = _make_runner()

    runner.run()

    mock_wait.assert_called_once_with(60)


# ---------- Gestione errore ----------


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_run_logs_error_on_operational_exception(mock_wait: MagicMock) -> None:
    """Se il ciclo fallisce con un errore operativo (ExchangeError), il runner logga
    l'errore con correlation ID e il loop continua."""
    mock_event_logger = MagicMock()
    mock_workflow = MagicMock()
    mock_workflow.run_cycle.side_effect = ExchangeError("errore di test")
    runner = _make_runner(event_logger=mock_event_logger, workflow=mock_workflow)

    runner.run()

    mock_event_logger.log_error.assert_called_once()
    call_kwargs = mock_event_logger.log_error.call_args.kwargs
    assert call_kwargs["symbol"] == "BTCUSDC"
    assert call_kwargs["trading_mode"] == "DEMO"
    assert "errore di test" in call_kwargs["error"]
    assert len(call_kwargs["correlation_id"]) == 8


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_run_passes_partial_results_to_log_error_on_cycle_execution_error(
    mock_wait: MagicMock,
) -> None:
    """Su CycleExecutionError, il runner passa i parziali e str(original) a log_error."""
    partial_market_analysis = MarketAnalysis(
        market_bias=MarketBias.BULLISH,
        signal_strength=0.7,
        confidence=0.7,
        summary="Trend rialzista",
        suggested_action=SuggestedAction.LONG_BIAS,
    )
    partial_trade_proposal = TradeProposal(
        action=TradeAction.BUY,
        order_type=OrderType.MARKET,
        confidence=0.8,
        reason="Segnale forte",
    )
    partial_risk_assessment = RiskAssessment(
        risk_decision=RiskDecision.APPROVE,
        confidence=0.9,
        reason="Ok",
    )
    original_exc = LlmError("Risposta vuota dal provider")
    cycle_exc = CycleExecutionError(
        "Execution Trader failed",
        original=original_exc,
        market_analysis=partial_market_analysis,
        trade_proposal=partial_trade_proposal,
        risk_assessment=partial_risk_assessment,
    )
    mock_event_logger = MagicMock()
    mock_workflow = MagicMock()
    mock_workflow.run_cycle.side_effect = cycle_exc
    runner = _make_runner(event_logger=mock_event_logger, workflow=mock_workflow)

    runner.run()

    mock_event_logger.log_error.assert_called_once()
    call_kwargs = mock_event_logger.log_error.call_args.kwargs
    assert call_kwargs["error"] == "Risposta vuota dal provider"
    assert call_kwargs["market_analysis"] is partial_market_analysis
    assert call_kwargs["trade_proposal"] is partial_trade_proposal
    assert call_kwargs["risk_assessment"] is partial_risk_assessment
    assert len(call_kwargs["correlation_id"]) == 8


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
    mock_workflow = MagicMock()
    mock_workflow.run_cycle.return_value.execution_report.was_executed = False
    runner = _make_runner(telegram_notifier=mock_notifier, workflow=mock_workflow)

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
    mock_workflow = MagicMock()
    mock_workflow.run_cycle.return_value.execution_report.was_executed = False
    runner = _make_runner(telegram_notifier=mock_notifier, workflow=mock_workflow)

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
def test_run_sends_error_notification_on_operational_exception(mock_wait: MagicMock) -> None:
    """Su errore operativo (LlmError) nel ciclo, il runner deve inviare una notifica Telegram
    con correlation ID e tipo eccezione, senza str(exc)."""
    mock_notifier = MagicMock(spec=TelegramNotifier)
    mock_workflow = MagicMock()
    mock_workflow.run_cycle.side_effect = LlmError("Risposta vuota dal provider OpenAI.")
    runner = _make_runner(workflow=mock_workflow, telegram_notifier=mock_notifier)

    runner.run()

    texts = [call.args[0] for call in mock_notifier.send_message.call_args_list]
    error_text = next((t for t in texts if "ERROR" in t), None)
    assert error_text is not None
    assert "Categoria:" in error_text
    assert "Risposta LLM non valida" in error_text
    assert "Error ID:" in error_text


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
    assert not any("EXECUTED" in t for t in texts)


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_run_sends_unprotected_position_alert_when_flag_set(
    mock_wait: MagicMock,
) -> None:
    """Con flag unprotected_position=True in execution_details, deve arrivare l'alert dedicato."""
    mock_notifier = MagicMock(spec=TelegramNotifier)
    mock_workflow = MagicMock()
    mock_result = mock_workflow.run_cycle.return_value
    mock_result.execution_report.was_executed = False
    mock_result.execution_report.execution_status = ExecutionStatus.FAILED
    mock_result.execution_report.execution_details = {
        "unprotected_position": True,
        "cancelled_order_id": "888",
    }
    runner = _make_runner(workflow=mock_workflow, telegram_notifier=mock_notifier)

    runner.run()

    texts = [call.args[0] for call in mock_notifier.send_message.call_args_list]
    assert any("888" in t for t in texts)
    assert any(
        "ALARM" in t or "SCOPERTA" in t or "scoperta" in t.lower() for t in texts
    )


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_run_does_not_send_unprotected_alert_on_normal_failed(
    mock_wait: MagicMock,
) -> None:
    """Un FAILED senza flag unprotected_position NON deve inviare l'alert posizione scoperta."""
    mock_notifier = MagicMock(spec=TelegramNotifier)
    mock_workflow = MagicMock()
    mock_result = mock_workflow.run_cycle.return_value
    mock_result.execution_report.was_executed = False
    mock_result.execution_report.execution_status = ExecutionStatus.FAILED
    mock_result.execution_report.execution_details = {}
    runner = _make_runner(workflow=mock_workflow, telegram_notifier=mock_notifier)

    runner.run()

    texts = [call.args[0] for call in mock_notifier.send_message.call_args_list]
    assert not any("SCOPERTA" in t or "ALARM" in t for t in texts)


# ---------- Performance Reviewer trigger ----------


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_maybe_run_performance_review_skips_if_today_report_exists(
    mock_wait: MagicMock, tmp_path: Path,
) -> None:
    """Se il report di oggi esiste gia, il Reviewer non viene chiamato."""
    today_file = tmp_path / f"{date.today().isoformat()}.md"
    today_file.write_text("existing report", encoding="utf-8")

    mock_reviewer = MagicMock()
    runner = _make_runner(
        performance_reviewer=mock_reviewer,
        performance_reports_dir=tmp_path,
    )

    runner.run()

    mock_reviewer.run.assert_not_called()


@patch("src.core.performance_review_runner.build_performance_stats")
@patch("src.core.performance_review_runner.load_recent_events", return_value=[])
@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_maybe_run_performance_review_writes_report_when_missing(
    mock_wait: MagicMock,
    mock_events: MagicMock,
    mock_build: MagicMock,
    tmp_path: Path,
) -> None:
    """Se non c'e report per oggi, il Reviewer viene eseguito e il file viene scritto."""
    mock_build.return_value = PerformanceStats(
        period_start="2026-04-14",
        period_end="2026-04-20",
        total_cycles=10,
        buy_executed=1,
        sell_executed=0,
        hold_count=9,
        sell_failed=0,
        hold_ratio=0.9,
        strong_bullish_ignored=0,
        strong_bearish_ignored=0,
        realized_pnl_usdc=0.0,
        avg_pnl_pct=0.0,
        days_without_executed_trade=3,
    )
    mock_reviewer = MagicMock()
    mock_reviewer.run.return_value = PerformanceReview(
        summary="Test review",
        mandate_adherence=MandateAdherence.ALIGNED,
        suggestions=["s1"],
    )

    runner = _make_runner(
        performance_reviewer=mock_reviewer,
        performance_reports_dir=tmp_path,
    )

    runner.run()

    mock_reviewer.run.assert_called_once()
    today_file = tmp_path / f"{date.today().isoformat()}.md"
    assert today_file.exists()


@patch(
    "src.core.performance_review_runner.load_recent_events",
    side_effect=RuntimeError("boom"),
)
@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_maybe_run_performance_review_failure_does_not_block_cycle(
    mock_wait: MagicMock,
    mock_events: MagicMock,
    tmp_path: Path,
) -> None:
    """Se il Reviewer fallisce, il ciclo procede comunque."""
    mock_workflow = MagicMock()
    mock_result = mock_workflow.run_cycle.return_value
    mock_result.execution_report.was_executed = False

    runner = _make_runner(
        workflow=mock_workflow,
        performance_reports_dir=tmp_path,
    )

    runner.run()

    mock_workflow.run_cycle.assert_called_once()


def test_load_latest_performance_review_returns_empty_if_dir_missing(
    tmp_path: Path,
) -> None:
    runner = _make_runner(performance_reports_dir=tmp_path / "missing")

    assert runner._review_runner.load_latest_review() == ""


def test_load_latest_performance_review_returns_file_content(
    tmp_path: Path,
) -> None:
    (tmp_path / "2026-04-18.md").write_text("older", encoding="utf-8")
    (tmp_path / "2026-04-19.md").write_text("latest content", encoding="utf-8")

    runner = _make_runner(performance_reports_dir=tmp_path)

    assert runner._review_runner.load_latest_review() == "latest content"


# ---------- Cycle skip ----------


_ENABLED_SKIP_CONFIG = CycleSkipConfig(
    enabled=True,
    max_consecutive_skips=4,
    price_delta_pct=0.5,
    rsi_delta=2.0,
    macd_sign_must_match=True,
    require_no_order_events=True,
    require_previous_action_hold=True,
)


def _stable_market() -> MarketDataSnapshot:
    return MarketDataSnapshot(
        symbol="BTCUSDC",
        price=100.0,
        indicators={"rsi": 50.0, "macd": 1.0, "macd_signal": 0.5},
    )


def _empty_portfolio() -> PortfolioState:
    return PortfolioState(
        usdc_balance=1000.0,
        usdc_balance_total=1000.0,
        usdc_value=1000.0,
        portfolio_qty_free=0.0,
        portfolio_qty_total=0.0,
        open_orders=[],
    )


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_cycle_is_skipped_when_context_unchanged(mock_wait: MagicMock) -> None:
    """Con cycle skip attivo e contesto invariato, il workflow NON viene chiamato."""
    mock_exchange = MagicMock()
    mock_exchange.get_market_snapshot.return_value = _stable_market()
    mock_exchange.get_portfolio_state.return_value = _empty_portfolio()
    mock_workflow = MagicMock()
    mock_event_logger = MagicMock()

    runner = _make_runner(
        exchange_client=mock_exchange,
        workflow=mock_workflow,
        event_logger=mock_event_logger,
        cycle_skip_config=_ENABLED_SKIP_CONFIG,
    )
    runner._cycle_skip_handler._previous_snapshot = CycleContextSnapshot(
        price=100.0,
        rsi=50.0,
        macd=1.0,
        macd_signal=0.5,
        previous_action=TradeAction.HOLD,
        open_order_ids=set(),
    )

    runner.run()

    mock_workflow.run_cycle.assert_not_called()
    mock_event_logger.log_skipped_cycle.assert_called_once()
    assert runner._cycle_skip_handler._consecutive_skips == 1


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_cycle_runs_normally_when_skip_disabled(mock_wait: MagicMock) -> None:
    """Con cycle skip disabilitato, il workflow viene sempre chiamato."""
    mock_exchange = MagicMock()
    mock_exchange.get_market_snapshot.return_value = _stable_market()
    mock_exchange.get_portfolio_state.return_value = _empty_portfolio()
    mock_workflow = MagicMock()

    runner = _make_runner(
        exchange_client=mock_exchange,
        workflow=mock_workflow,
    )
    runner._cycle_skip_handler._previous_snapshot = CycleContextSnapshot(
        price=100.0,
        rsi=50.0,
        macd=1.0,
        macd_signal=0.5,
        previous_action=TradeAction.HOLD,
        open_order_ids=set(),
    )

    runner.run()

    mock_workflow.run_cycle.assert_called_once()


# --- Test per _classify_error ---


def test_classify_error_overloaded_is_external_api() -> None:
    """OverloadedError (Anthropic 529) → API esterna non disponibile."""
    OverloadedError = type("OverloadedError", (Exception,), {})
    assert _classify_error(OverloadedError("overloaded")) == "API esterna non disponibile"


def test_classify_error_internal_server_error_is_external_api() -> None:
    """InternalServerError (500) → API esterna non disponibile."""
    InternalServerError = type("InternalServerError", (Exception,), {})
    assert _classify_error(InternalServerError("internal server error")) == "API esterna non disponibile"


def test_classify_error_api_connection_error_is_external_api() -> None:
    """APIConnectionError → API esterna non disponibile."""
    APIConnectionError = type("APIConnectionError", (Exception,), {})
    assert _classify_error(APIConnectionError("connection error")) == "API esterna non disponibile"


def test_classify_error_api_timeout_error_is_external_api() -> None:
    """APITimeoutError → API esterna non disponibile."""
    APITimeoutError = type("APITimeoutError", (Exception,), {})
    assert _classify_error(APITimeoutError("timeout")) == "API esterna non disponibile"


def test_classify_error_binance_request_exception_is_external_api() -> None:
    """BinanceRequestException → API esterna non disponibile."""
    BinanceRequestException = type("BinanceRequestException", (Exception,), {})
    assert _classify_error(BinanceRequestException("connection refused")) == "API esterna non disponibile"


def test_classify_error_binance_api_exception_502_is_external_api() -> None:
    """BinanceAPIException con status_code 502 → API esterna non disponibile."""
    BinanceAPIException = type("BinanceAPIException", (Exception,), {})
    exc = BinanceAPIException("bad gateway")
    exc.status_code = 502  # type: ignore[attr-defined]
    assert _classify_error(exc) == "API esterna non disponibile"


def test_classify_error_binance_api_exception_code0_is_external_api() -> None:
    """BinanceAPIException con status_code 0 (risposta HTML non JSON) → API esterna non disponibile."""
    BinanceAPIException = type("BinanceAPIException", (Exception,), {})
    exc = BinanceAPIException("invalid json")
    exc.status_code = 0  # type: ignore[attr-defined]
    assert _classify_error(exc) == "API esterna non disponibile"


def test_classify_error_rate_limit_error_is_rate_limit() -> None:
    """RateLimitError (429) → Rate limit API."""
    RateLimitError = type("RateLimitError", (Exception,), {})
    assert _classify_error(RateLimitError("rate limited")) == "Rate limit API"


def test_classify_error_runtime_error_empty_response_is_llm_invalid() -> None:
    """RuntimeError con 'risposta vuota' nel messaggio → Risposta LLM non valida."""
    exc = RuntimeError("Risposta vuota dal provider Anthropic.")
    assert _classify_error(exc) == "Risposta LLM non valida"


def test_classify_error_runtime_error_json_decode_is_llm_invalid() -> None:
    """RuntimeError con 'decodificare' nel messaggio → Risposta LLM non valida."""
    exc = RuntimeError("Impossibile decodificare la risposta JSON di OpenAI.")
    assert _classify_error(exc) == "Risposta LLM non valida"


def test_classify_error_runtime_error_empty_json_is_llm_invalid() -> None:
    """RuntimeError con 'json vuoto' nel messaggio → Risposta LLM non valida."""
    exc = RuntimeError("Il provider Gemini ha risposto con un JSON vuoto.")
    assert _classify_error(exc) == "Risposta LLM non valida"


def test_classify_error_value_error_is_internal() -> None:
    """ValueError generico → Errore interno."""
    exc = ValueError("campo mancante")
    assert _classify_error(exc) == "Errore interno"


def test_classify_error_generic_runtime_error_is_internal() -> None:
    """RuntimeError senza keyword LLM → Errore interno."""
    exc = RuntimeError("Unexpected state in runner")
    assert _classify_error(exc) == "Errore interno"


def test_classify_error_llm_error_is_llm_invalid() -> None:
    """LlmError → Risposta LLM non valida."""
    exc = LlmError("Risposta vuota dal provider Anthropic.")
    assert _classify_error(exc) == "Risposta LLM non valida"


def test_classify_error_exchange_error_is_external_api() -> None:
    """ExchangeError → API esterna non disponibile."""
    exc = ExchangeError("BinanceRequestException: connection refused")
    assert _classify_error(exc) == "API esterna non disponibile"


def test_unexpected_exception_does_not_propagate_from_run_single_cycle() -> None:
    """Un bug imprevisto (AttributeError) NON deve propagarsi: il circuit breaker
    intercetta anche i bug imprevisti per evitare crash loop del processo."""
    mock_event_logger = MagicMock()
    mock_notifier = MagicMock(spec=TelegramNotifier)
    mock_workflow = MagicMock()
    mock_workflow.run_cycle.side_effect = AttributeError("bug imprevisto")
    runner = _make_runner(
        event_logger=mock_event_logger,
        workflow=mock_workflow,
        telegram_notifier=mock_notifier,
    )

    runner._run_single_cycle()  # non deve sollevare

    mock_event_logger.log_error.assert_called_once()
    texts = [call.args[0] for call in mock_notifier.send_message.call_args_list]
    assert any("ERROR" in t for t in texts)
    assert runner._circuit_breaker.consecutive_count == 1


def test_unexpected_exception_repeated_trips_circuit_breaker_and_pauses_loop() -> None:
    """run() non termina al primo bug imprevisto: continua il loop e dopo 3 errori
    identici scatta il circuit breaker, che sospende i cicli successivi."""
    mock_notifier = MagicMock(spec=TelegramNotifier)
    mock_workflow = MagicMock()
    mock_workflow.run_cycle.side_effect = AttributeError("bug nel workflow")
    runner = _make_runner(workflow=mock_workflow, telegram_notifier=mock_notifier)

    # 3 cicli con errore (counter 1, 2, 3 → trip), poi 2 cicli skippati, poi stop.
    with patch.object(
        runner._shutdown_event, "wait",
        side_effect=[True, True, True, True, KeyboardInterrupt],
    ):
        runner.run()

    # Workflow chiamato esattamente 3 volte (4° e 5° giro: bot in pausa).
    assert mock_workflow.run_cycle.call_count == 3
    assert runner._circuit_breaker.is_tripped()

    texts = [call.args[0] for call in mock_notifier.send_message.call_args_list]
    # 3 notifiche di errore + 1 di circuit breaker scattato.
    assert sum("ERROR" in t for t in texts) == 3
    assert sum("CIRCUIT BREAKER" in t for t in texts) == 1


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_first_cycle_is_not_skipped_even_with_skip_enabled(
    mock_wait: MagicMock,
) -> None:
    """Il primo ciclo (snapshot=None) non viene mai saltato."""
    mock_exchange = MagicMock()
    mock_exchange.get_market_snapshot.return_value = _stable_market()
    mock_exchange.get_portfolio_state.return_value = _empty_portfolio()
    mock_workflow = MagicMock()

    runner = _make_runner(
        exchange_client=mock_exchange,
        workflow=mock_workflow,
        cycle_skip_config=_ENABLED_SKIP_CONFIG,
    )

    runner.run()

    mock_workflow.run_cycle.assert_called_once()


# ---------- Circuit breaker ----------


def test_circuit_breaker_reads_threshold_and_interval_from_trading_config() -> None:
    """Il runner deve leggere threshold e log_interval_seconds da trading_config."""
    custom_config = {
        **_MOCK_TRADING_CONFIG,
        "circuit_breaker": {
            "threshold": 5,
            "log_interval_seconds": 1800,
        },
    }
    with patch(
        "src.core.runner.load_trading_config", return_value=custom_config,
    ), patch(
        "src.core.runner.load_cycle_skip_config",
        return_value=_DEFAULT_DISABLED_SKIP_CONFIG,
    ):
        runner = TradingRunner(
            workflow=MagicMock(),
            event_logger=MagicMock(),
            logger=logging.getLogger("mdk_crypto_trading.test_cb_config"),
            settings=_make_settings(),
            symbol="BTCUSDC",
            exchange_client=MagicMock(),
            memory_manager=MagicMock(spec=MemoryManager),
            performance_reviewer=MagicMock(),
        )

    assert runner._circuit_breaker.threshold == 5
    assert runner._circuit_breaker._pause_log_interval_seconds == 1800.0


def _stop_after_n_waits_side_effect(n: int):
    call_count = {"n": 0}

    def _side_effect(*_args: object, **_kwargs: object) -> None:
        call_count["n"] += 1
        if call_count["n"] >= n:
            raise KeyboardInterrupt

    return _side_effect


def test_circuit_breaker_trips_after_three_identical_errors() -> None:
    """Tre errori identici consecutivi fanno scattare il breaker."""
    mock_notifier = MagicMock(spec=TelegramNotifier)
    mock_workflow = MagicMock()
    mock_workflow.run_cycle.side_effect = LlmError("same error")

    breaker = CircuitBreaker(logging.getLogger("test_cb_trip"), threshold=3)
    runner = _make_runner(
        workflow=mock_workflow,
        telegram_notifier=mock_notifier,
        circuit_breaker=breaker,
    )

    with patch(
        "src.core.runner.threading.Event.wait",
        side_effect=_stop_after_n_waits_side_effect(4),
    ):
        runner.run()

    assert breaker.is_tripped() is True
    assert mock_workflow.run_cycle.call_count == 3
    texts = [call.args[0] for call in mock_notifier.send_message.call_args_list]
    cb_texts = [t for t in texts if "CIRCUIT BREAKER" in t]
    assert len(cb_texts) == 1


def test_circuit_breaker_does_not_trip_on_different_errors() -> None:
    """Errori con signature diversa non fanno scattare il breaker."""
    mock_workflow = MagicMock()
    mock_workflow.run_cycle.side_effect = [
        LlmError("error A"),
        LlmError("error B"),
        LlmError("error C"),
    ]

    breaker = CircuitBreaker(logging.getLogger("test_cb_diff"), threshold=3)
    runner = _make_runner(workflow=mock_workflow, circuit_breaker=breaker)

    with patch(
        "src.core.runner.threading.Event.wait",
        side_effect=_stop_after_n_waits_side_effect(3),
    ):
        runner.run()

    assert breaker.is_tripped() is False
    assert mock_workflow.run_cycle.call_count == 3


def test_circuit_breaker_resets_on_success() -> None:
    """Un ciclo riuscito tra due errori identici azzera il contatore."""
    mock_workflow = MagicMock()
    success_result = MagicMock()
    success_result.execution_report.was_executed = False
    mock_workflow.run_cycle.side_effect = [
        LlmError("same error"),
        LlmError("same error"),
        success_result,
        LlmError("same error"),
    ]

    breaker = CircuitBreaker(logging.getLogger("test_cb_reset"), threshold=3)
    runner = _make_runner(workflow=mock_workflow, circuit_breaker=breaker)

    with patch(
        "src.core.runner.threading.Event.wait",
        side_effect=_stop_after_n_waits_side_effect(4),
    ):
        runner.run()

    assert breaker.is_tripped() is False
    assert mock_workflow.run_cycle.call_count == 4
    assert breaker.consecutive_count == 1


def test_main_loop_skips_cycles_when_breaker_tripped() -> None:
    """Se il breaker e' gia trippato, _run_single_cycle non viene chiamato."""
    mock_workflow = MagicMock()
    breaker = CircuitBreaker(logging.getLogger("test_cb_skip"), threshold=3)
    breaker.record_error("sig")
    breaker.record_error("sig")
    breaker.record_error("sig")
    assert breaker.is_tripped() is True

    runner = _make_runner(workflow=mock_workflow, circuit_breaker=breaker)

    with patch(
        "src.core.runner.threading.Event.wait",
        side_effect=_stop_after_n_waits_side_effect(3),
    ), patch.object(runner, "_touch_heartbeat") as mock_heartbeat:
        runner.run()

    mock_workflow.run_cycle.assert_not_called()
    assert mock_heartbeat.call_count >= 2


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_build_cycle_input_sets_oco_review_required_true(mock_wait: MagicMock) -> None:
    """Se un OCO è vecchio abbastanza, il flag oco_review_required arriva nel TradingCycleInput."""
    mock_exchange = MagicMock()
    portfolio = PortfolioState(
        usdc_balance=500.0,
        usdc_balance_total=500.0,
        usdc_value=500.0,
        portfolio_qty_free=0.005,
        portfolio_qty_total=0.005,
        open_orders=[
            {"type": "LIMIT_MAKER", "orderListId": 5, "age_hours": 30.0},
        ],
    )
    mock_exchange.get_market_snapshot.return_value = MarketDataSnapshot(
        symbol="BTCUSDC", price=90000.0,
    )
    mock_exchange.get_portfolio_state.return_value = portfolio

    captured_input: dict[str, object] = {}

    mock_workflow = MagicMock()
    mock_workflow.run_cycle.side_effect = lambda ci: (_ for _ in ()).throw(
        KeyboardInterrupt
    )

    class _CapturingWorkflow:
        def run_cycle(self, cycle_input: Any) -> None:  # type: ignore[return]
            captured_input["oco_review_required"] = cycle_input.oco_review_required
            raise KeyboardInterrupt

    runner = _make_runner(
        exchange_client=mock_exchange,
        workflow=_CapturingWorkflow(),
    )
    runner._position_manager._oco_review_interval_hours = 24.0

    runner.run()

    assert captured_input.get("oco_review_required") is True


# ---------- Equity logging ----------


@patch("src.core.runner.threading.Event.wait", side_effect=KeyboardInterrupt)
def test_run_single_cycle_passes_equity_to_save_cycle(mock_wait: MagicMock) -> None:
    """_run_single_cycle deve calcolare l'equity e passarla a memory_manager.save_cycle."""
    mock_mm = MagicMock(spec=MemoryManager)
    mock_exchange = MagicMock()

    portfolio = PortfolioState(
        usdc_balance=400.0,
        usdc_balance_total=500.0,
        usdc_value=200.0,
        portfolio_qty_free=0.002,
        portfolio_qty_total=0.002,
    )
    mock_exchange.get_portfolio_state.return_value = portfolio
    mock_exchange.get_market_snapshot.return_value = MarketDataSnapshot(
        symbol="BTCUSDC", price=100000.0,
    )

    mock_workflow = MagicMock()
    mock_result = mock_workflow.run_cycle.return_value
    mock_result.execution_report.was_executed = False
    mock_result.execution_report.execution_status = ExecutionStatus.NOT_EXECUTED
    mock_result.execution_report.execution_details = {}

    runner = _make_runner(
        exchange_client=mock_exchange,
        workflow=mock_workflow,
        memory_manager=mock_mm,
    )
    runner.run()

    mock_mm.save_cycle.assert_called_once()
    call_kwargs = mock_mm.save_cycle.call_args.kwargs
    assert call_kwargs["symbol"] == "BTCUSDC"
    assert call_kwargs["current_price"] == pytest.approx(100000.0)
    # equity = usdc_balance_total (500) + usdc_value (200) = 700
    # (usdc_balance libero = 400 NON deve essere usato: cattura la regressione)
    assert call_kwargs["equity_usdc"] == pytest.approx(700.0)
