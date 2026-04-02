from __future__ import annotations

import logging
import time

from src.core.contracts import (
    OperationConstraints,
    OrderType,
    TradingCycleInput,
    TradingCycleResult,
)
from src.core.workflow import TradingWorkflow
from src.integrations.exchange.base_exchange_client import BaseExchangeClient
from src.utils.config import AppSettings, load_trading_config
from src.utils.event_logger import EventLogger
from src.utils.memory_manager import MemoryManager
from src.utils.telegram_notifier import TelegramNotifier


class TradingRunner:
    """Loop operativo che esegue TradingWorkflow in modo ciclico."""

    def __init__(
        self,
        workflow: TradingWorkflow,
        event_logger: EventLogger,
        logger: logging.Logger,
        settings: AppSettings,
        symbol: str,
        exchange_client: BaseExchangeClient,
        memory_manager: MemoryManager,
        telegram_notifier: TelegramNotifier | None = None,
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

    def run(self) -> None:
        """Avvia il loop operativo. Esce solo su KeyboardInterrupt."""
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

        if self._telegram_notifier:
            self._telegram_notifier.send_message(
                f"<b>Bot AVVIATO</b>\n"
                f"Simbolo: {self._symbol}\n"
                f"Modo: {self._settings.trading_mode.value}\n"
                f"Intervallo: {self._settings.cycle_interval_seconds}s"
            )

        try:
            while True:
                self._run_single_cycle()
                self._logger.info(
                    "Prossimo ciclo tra %d secondi",
                    self._settings.cycle_interval_seconds,
                )
                time.sleep(self._settings.cycle_interval_seconds)
        except KeyboardInterrupt:
            self._logger.info("Shutdown richiesto. Arresto pulito del runner.")
            if self._telegram_notifier:
                self._telegram_notifier.send_message(
                    f"<b>Bot FERMATO</b>\nSimbolo: {self._symbol}"
                )

    def _run_single_cycle(self) -> None:
        """Esegue un singolo ciclo operativo con gestione degli errori."""
        self._logger.info("Inizio ciclo operativo")
        try:
            cycle_input = self._build_cycle_input()
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
            if self._telegram_notifier and result.execution_report.was_executed:
                self._telegram_notifier.send_message(
                    self._build_order_notification(result)
                )
            self._logger.info("Ciclo completato con successo")
        except Exception as exc:
            self._logger.error("Errore durante il ciclo: %s", exc)
            self._event_logger.log_error(
                symbol=self._symbol,
                trading_mode=self._settings.trading_mode.value,
                error=str(exc),
            )
            if self._telegram_notifier:
                self._telegram_notifier.send_message(
                    f"<b>ERRORE nel ciclo</b>\n"
                    f"Simbolo: {self._symbol}\n"
                    f"Errore: {exc}"
                )

    def _build_cycle_input(self) -> TradingCycleInput:
        """Raccoglie dati di mercato e portafoglio dall'exchange e costruisce l'input."""
        market_data = self._exchange_client.get_market_snapshot(self._symbol)
        portfolio = self._exchange_client.get_portfolio_state(self._symbol)
        constraints = OperationConstraints(
            cycle_interval_seconds=self._settings.cycle_interval_seconds,
            min_order_usdc=float(self._trading_config.get("min_order_usdc", 10.0)),
        )
        return TradingCycleInput(
            symbol=self._symbol,
            market_data=market_data,
            portfolio=portfolio,
            constraints=constraints,
            ia_memory=self._memory_manager.get_memory(self._symbol),
            performance_summary=self._memory_manager.get_performance_summary(self._symbol),
            recent_performance=self._memory_manager.get_recent_performance(self._symbol),
        )

    def _build_order_notification(self, result: TradingCycleResult) -> str:
        """Costruisce il testo della notifica per un ordine eseguito."""
        report = result.execution_report
        proposal = result.trade_proposal
        details = proposal.details

        lines: list[str] = [
            "<b>Ordine ESEGUITO</b>",
            f"Azione: {report.executed_action.value}",
            f"Tipo: {report.order_type.value}",
        ]

        if details.quantity is not None:
            lines.append(f"Quantità: {details.quantity}")

        if report.order_type is OrderType.MARKET:
            exec_d = report.execution_details
            cum_quote = exec_d.get("cummulativeQuoteQty")
            exec_qty = exec_d.get("executedQty")
            if cum_quote and exec_qty:
                try:
                    avg_price = float(cum_quote) / float(exec_qty)
                    lines.append(f"Prezzo: {avg_price:.2f}")
                    lines.append(f"Valore: {float(cum_quote):.2f} USDC")
                except (ValueError, ZeroDivisionError):
                    pass
        elif report.order_type is OrderType.LIMIT:
            if details.price is not None:
                lines.append(f"Prezzo: {details.price:.2f}")
            notional = details.estimated_notional()
            if notional is not None:
                lines.append(f"Valore stimato: {notional:.2f} USDC")

        lines.append(f"Confidenza DM: {proposal.confidence:.2f}")
        lines.append(f"Simbolo: {self._symbol}")
        lines.append(f"Modo: {self._settings.trading_mode.value}")

        return "\n".join(lines)
