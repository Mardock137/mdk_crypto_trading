from __future__ import annotations

import logging
from typing import Any

from src.agents.base_agent import BaseAgent
from src.core.contracts import (
    ExecutionInput,
    ExecutionReport,
    ExecutionStatus,
    OrderType,
    TradeAction,
)
from src.integrations.exchange.base_exchange_client import BaseExchangeClient

_logger = logging.getLogger(__name__)


class ExecutionTraderAgent(BaseAgent[ExecutionInput, ExecutionReport]):
    def __init__(
        self,
        exchange_client: BaseExchangeClient,
        kill_switch: bool = False,
    ) -> None:
        super().__init__(name="execution_trader")
        self._exchange = exchange_client
        self._kill_switch = kill_switch

    def run(self, agent_input: ExecutionInput) -> ExecutionReport:
        proposal = agent_input.proposal
        risk = agent_input.risk_assessment

        if self._kill_switch:
            return ExecutionReport(
                execution_status=ExecutionStatus.NOT_EXECUTED,
                executed_action=proposal.action,
                order_type=proposal.order_type,
                reason="Kill switch attivo: operazione bloccata.",
            )

        if not risk.is_approved:
            return ExecutionReport(
                execution_status=ExecutionStatus.NOT_EXECUTED,
                executed_action=proposal.action,
                order_type=proposal.order_type,
                reason=f"Proposta non approvata dal Risk Manager: {risk.reason}",
            )

        if proposal.is_hold:
            return ExecutionReport(
                execution_status=ExecutionStatus.NOT_EXECUTED,
                executed_action=TradeAction.HOLD,
                order_type=OrderType.NONE,
                reason="HOLD: nessuna operazione da eseguire.",
            )

        try:
            details = self._execute_order(agent_input)
        except Exception as exc:
            _logger.error("Esecuzione ordine fallita: %s", exc, exc_info=True)
            return ExecutionReport(
                execution_status=ExecutionStatus.FAILED,
                executed_action=proposal.action,
                order_type=proposal.order_type,
                reason=f"Errore durante l'esecuzione: {exc}",
            )

        return ExecutionReport(
            execution_status=ExecutionStatus.EXECUTED,
            executed_action=proposal.action,
            order_type=proposal.order_type,
            reason="Ordine eseguito con successo.",
            execution_details=details,
        )

    def _execute_order(self, agent_input: ExecutionInput) -> dict[str, Any]:
        """Esegue l'ordine sull'exchange e ritorna i dettagli della risposta."""
        proposal = agent_input.proposal
        symbol = agent_input.symbol
        action = proposal.action
        details = proposal.details

        if action is TradeAction.CANCEL_AND_REPLACE_ORDER:
            if details.order_id is None:
                raise ValueError("order_id is required for CANCEL_AND_REPLACE_ORDER.")
            if details.side is None:
                raise ValueError("side is required for CANCEL_AND_REPLACE_ORDER.")
            if details.quantity is None:
                raise ValueError("quantity is required for CANCEL_AND_REPLACE_ORDER.")
            if details.price is None:
                raise ValueError("price is required for CANCEL_AND_REPLACE_ORDER.")
            self._exchange.cancel_order(symbol, details.order_id)
            try:
                return self._exchange.place_limit_order(
                    symbol, details.side.value, details.quantity, details.price,
                )
            except Exception as exc:
                _logger.warning(
                    "CRITICAL: Order %s cancelled but replacement failed: %s. "
                    "Manual intervention may be required.",
                    details.order_id,
                    exc,
                )
                raise RuntimeError(
                    f"CRITICAL: Order {details.order_id} cancelled but replacement "
                    f"failed: {exc}. Manual intervention may be required."
                ) from exc

        if details.quantity is None:
            raise ValueError("quantity is required for BUY/SELL orders.")
        side = action.value  # "BUY" o "SELL"

        if proposal.order_type is OrderType.MARKET:
            return self._exchange.place_market_order(
                symbol, side, details.quantity,
            )

        if details.price is None:
            raise ValueError("price is required for LIMIT orders.")
        return self._exchange.place_limit_order(
            symbol, side, details.quantity, details.price,
        )
