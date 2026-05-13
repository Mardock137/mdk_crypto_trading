from __future__ import annotations

import logging
import signal
import threading
import types
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.agents.performance_reviewer import PerformanceReviewerAgent
from src.core import notifications
from src.core.contracts import (
    MarketDataSnapshot,
    OperationConstraints,
    PortfolioState,
    TradingCycleInput,
)
from src.core.exceptions import MdkTradingError
from src.core.cycle_skip_handler import CycleSkipHandler
from src.core.performance_review_runner import PerformanceReviewRunner
from src.core.workflow import TradingWorkflow
from src.integrations.exchange.base_exchange_client import BaseExchangeClient
from src.utils.config import (
    AppSettings,
    load_cycle_skip_config,
    load_mandate,
    load_trading_config,
)
from src.utils.event_logger import EventLogger
from src.utils.memory_manager import MemoryManager
from src.utils.telegram_notifier import TelegramNotifier

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_PERFORMANCE_REPORTS_DIR = _PROJECT_ROOT / "data/performance_reports"
_HEARTBEAT_PATH = _PROJECT_ROOT / "data/heartbeat"


def _classify_error(exc: Exception) -> str:
    """Classifica un'eccezione in una categoria leggibile per la notifica Telegram.

    La classificazione avviene sul nome della classe e sul testo dell'errore,
    senza import aggiuntivi delle librerie specifiche dei provider.
    """
    exc_class = type(exc).__name__
    exc_msg = str(exc).lower()

    if exc_class in {
        "OverloadedError",
        "InternalServerError",
        "APIConnectionError",
        "APITimeoutError",
        "BinanceRequestException",
    }:
        return "API esterna non disponibile"

    if exc_class == "BinanceAPIException":
        code = getattr(exc, "status_code", 0)
        if code == 0 or code >= 500:
            return "API esterna non disponibile"

    if exc_class == "RateLimitError":
        return "Rate limit API"

    if exc_class == "LlmError" or (
        exc_class == "RuntimeError"
        and any(kw in exc_msg for kw in ("risposta vuota", "json vuoto", "decodificare"))
    ):
        return "Risposta LLM non valida"

    if exc_class == "ExchangeError":
        return "API esterna non disponibile"

    return "Errore interno"


class TradingRunner:
    """Loop operativo che esegue TradingWorkflow in modo ciclico.

    Direttore d'orchestra: gestisce loop, segnali e notifiche, delegando
    le decisioni specialistiche a ``CycleSkipHandler`` (skip deterministico)
    e ``PerformanceReviewRunner`` (review giornaliero).
    """

    def __init__(
        self,
        workflow: TradingWorkflow,
        event_logger: EventLogger,
        logger: logging.Logger,
        settings: AppSettings,
        symbol: str,
        exchange_client: BaseExchangeClient,
        memory_manager: MemoryManager,
        performance_reviewer: PerformanceReviewerAgent,
        telegram_notifier: TelegramNotifier | None = None,
        performance_reports_dir: Path = _PERFORMANCE_REPORTS_DIR,
    ) -> None:
        self._workflow = workflow
        self._event_logger = event_logger
        self._logger = logger
        self._settings = settings
        self._symbol = symbol
        self._exchange_client = exchange_client
        self._memory_manager = memory_manager
        self._telegram_notifier = telegram_notifier
        self._trading_config = load_trading_config()
        self._mandate = load_mandate(self._trading_config)
        self._shutdown_requested = False
        self._shutdown_event = threading.Event()

        self._cycle_skip_handler = CycleSkipHandler(
            symbol=symbol,
            trading_mode=settings.trading_mode.value,
            config=load_cycle_skip_config(),
            event_logger=event_logger,
            logger=logger,
        )
        self._review_runner = PerformanceReviewRunner(
            symbol=symbol,
            mandate=self._mandate,
            memory_manager=memory_manager,
            performance_reviewer=performance_reviewer,
            reports_dir=performance_reports_dir,
            logger=logger,
        )

    def run(self) -> None:
        """Avvia il loop operativo. Esce su KeyboardInterrupt o SIGTERM."""
        self._logger.info(
            "Avvio loop operativo — symbol=%s, mode=%s, intervallo=%ds",
            self._symbol,
            self._settings.trading_mode.value,
            self._settings.cycle_interval_seconds,
        )

        if self._settings.kill_switch:
            self._logger.warning(
                "Kill switch attivo: le operazioni saranno forzate a HOLD"
            )

        def _handle_signal(signum: int, frame: types.FrameType | None) -> None:
            self._logger.info("Segnale %d ricevuto. Shutdown richiesto.", signum)
            self._shutdown_requested = True
            self._shutdown_event.set()

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

        if self._telegram_notifier:
            self._telegram_notifier.send_message(
                notifications.build_startup_message(
                    symbol=self._symbol,
                    mode=self._settings.trading_mode.value,
                    interval_seconds=self._settings.cycle_interval_seconds,
                )
            )

        try:
            while not self._shutdown_requested:
                self._run_single_cycle()
                if self._shutdown_requested:
                    break
                self._logger.info(
                    "Prossimo ciclo tra %d secondi",
                    self._settings.cycle_interval_seconds,
                )
                self._shutdown_event.wait(self._settings.cycle_interval_seconds)
        except KeyboardInterrupt:
            pass
        except Exception as exc:
            self._logger.critical(
                "Errore critico imprevisto: il loop si arresta. %s", exc, exc_info=True,
            )
            if self._telegram_notifier:
                self._telegram_notifier.send_message(
                    notifications.build_error_message(
                        symbol=self._symbol,
                        correlation_id="CRITICAL",
                        error_category="Errore critico imprevisto",
                    )
                )
            return

        self._logger.info("Shutdown richiesto. Arresto pulito del runner.")
        if self._telegram_notifier:
            self._telegram_notifier.send_message(
                notifications.build_stop_message(symbol=self._symbol)
            )

    def _touch_heartbeat(self) -> None:
        """Scrive il timestamp UTC corrente in data/heartbeat.

        Il file viene usato dal HEALTHCHECK Docker per verificare che il loop
        sia ancora attivo. Gli errori I/O vengono ignorati per non bloccare il ciclo.
        """
        try:
            _HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
            _HEARTBEAT_PATH.write_text(
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )
        except OSError:
            pass

    def _run_single_cycle(self) -> None:
        """Esegue un singolo ciclo operativo con gestione degli errori.

        Se un'eccezione interrompe il ciclo, lo stato del ``CycleSkipHandler``
        non viene aggiornato: il ciclo successivo partirà quindi sempre con
        la catena LLM completa (nessun rischio di saltare dopo un fallimento).
        """
        self._touch_heartbeat()
        self._logger.info("Inizio ciclo operativo")
        self._review_runner.maybe_run_today()
        try:
            market_data = self._exchange_client.get_market_snapshot(self._symbol)
            portfolio = self._exchange_client.get_portfolio_state(self._symbol)
            self._augment_portfolio_with_open_position(market_data, portfolio)
            if self._cycle_skip_handler.try_skip(market_data, portfolio):
                return
            cycle_input = self._build_cycle_input(market_data, portfolio)
            result = self._workflow.run_cycle(cycle_input)
            self._logger.info(
                "Market Analyst → %s (strength: %.2f, confidence: %.2f)",
                result.market_analysis.market_bias.value,
                result.market_analysis.signal_strength,
                result.market_analysis.confidence,
            )
            self._logger.info(
                "Decision Maker → %s %s (confidence: %.2f)",
                result.trade_proposal.action.value,
                result.trade_proposal.order_type.value,
                result.trade_proposal.confidence,
            )
            self._logger.info(
                "Risk Manager → %s (confidence: %.2f)",
                result.risk_assessment.risk_decision.value,
                result.risk_assessment.confidence,
            )
            self._logger.info(
                "Execution → %s (%s)",
                result.execution_report.execution_status.value,
                result.execution_report.executed_action.value,
            )
            self._event_logger.log_cycle(
                symbol=self._symbol,
                trading_mode=self._settings.trading_mode.value,
                market_analysis=result.market_analysis,
                trade_proposal=result.trade_proposal,
                risk_assessment=result.risk_assessment,
                execution_report=result.execution_report,
            )
            self._memory_manager.save_cycle(
                symbol=self._symbol,
                result=result,
                current_price=cycle_input.market_data.price,
            )
            self._cycle_skip_handler.record_completed_cycle(
                market_data=cycle_input.market_data,
                portfolio=cycle_input.portfolio,
                proposed_action=result.trade_proposal.action,
            )
            if self._telegram_notifier and result.execution_report.was_executed:
                self._telegram_notifier.send_message(
                    notifications.build_order_notification(
                        symbol=self._symbol,
                        mode=self._settings.trading_mode.value,
                        result=result,
                    )
                )
            self._logger.info("Ciclo completato con successo")
        except (MdkTradingError, OSError) as exc:
            cid = uuid.uuid4().hex[:8]
            self._logger.error(
                "Errore operativo durante il ciclo [cid=%s]: %s", cid, exc, exc_info=True,
            )
            self._event_logger.log_error(
                symbol=self._symbol,
                trading_mode=self._settings.trading_mode.value,
                error=str(exc),
                correlation_id=cid,
            )
            if self._telegram_notifier:
                self._telegram_notifier.send_message(
                    notifications.build_error_message(
                        symbol=self._symbol,
                        correlation_id=cid,
                        error_category=_classify_error(exc),
                    )
                )
        except Exception as exc:
            cid = uuid.uuid4().hex[:8]
            self._logger.error(
                "Bug imprevisto durante il ciclo [cid=%s]: %s", cid, exc, exc_info=True,
            )
            self._event_logger.log_error(
                symbol=self._symbol,
                trading_mode=self._settings.trading_mode.value,
                error=str(exc),
                correlation_id=cid,
            )
            if self._telegram_notifier:
                self._telegram_notifier.send_message(
                    notifications.build_error_message(
                        symbol=self._symbol,
                        correlation_id=cid,
                        error_category=_classify_error(exc),
                    )
                )
            raise

    def _augment_portfolio_with_open_position(
        self,
        market_data: MarketDataSnapshot,
        portfolio: PortfolioState,
    ) -> None:
        """Calcola e popola avg_entry_price e unrealized_pnl_pct sul portafoglio.

        Usa la coda FIFO dei lotti BUY non ancora consumati gestita da MemoryManager.
        Se non c'e posizione aperta, mancano dati validi o un calcolo fallisce,
        lascia i campi a None senza interrompere il ciclo: si tratta di metadati
        opzionali che arricchiscono il prompt del Decision Maker.
        """
        try:
            qty_total = float(portfolio.portfolio_qty_total)
            price = float(market_data.price) if market_data.price is not None else None
        except (TypeError, ValueError):
            return
        if qty_total <= 0 or price is None or price <= 0:
            return
        try:
            open_pos = self._memory_manager.compute_open_position(self._symbol)
        except Exception:  # pragma: no cover — fallback difensivo
            return
        if not open_pos:
            return
        try:
            avg_entry = float(open_pos["avg_entry_price"])
        except (TypeError, ValueError, KeyError):
            return
        if avg_entry <= 0:
            return
        portfolio.avg_entry_price = avg_entry
        portfolio.unrealized_pnl_pct = round(
            (price - avg_entry) / avg_entry * 100, 4
        )

    def _build_cycle_input(
        self,
        market_data: MarketDataSnapshot,
        portfolio: PortfolioState,
    ) -> TradingCycleInput:
        """Costruisce l'input del ciclo a partire da market data e portafoglio già raccolti."""
        constraints = OperationConstraints(
            cycle_interval_seconds=self._settings.cycle_interval_seconds,
            min_order_usdc=float(self._trading_config.get("min_order_usdc", 10.0)),
            max_order_notional_usdc=float(
                self._trading_config.get("max_order_notional_usdc", 100.0)
            ),
        )
        return TradingCycleInput(
            symbol=self._symbol,
            market_data=market_data,
            portfolio=portfolio,
            constraints=constraints,
            mandate=self._mandate,
            decision_memory=self._memory_manager.get_memory(self._symbol),
            performance_summary=self._memory_manager.get_performance_summary(self._symbol),
            recent_performance=self._memory_manager.get_recent_performance(self._symbol),
            latest_performance_review=self._review_runner.load_latest_review(),
        )
