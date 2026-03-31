from __future__ import annotations

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


class ExecutionTraderAgent(BaseAgent[ExecutionInput, ExecutionReport]):
    def __init__(
        self,
        exchange_client: BaseExchangeClient,
        kill_switch: bool = False,
    ) -> None:
        super().__init__(name="execution_trader", prompt_name="execution_trader.md")
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
            assert details.order_id is not None
            assert details.side is not None
            assert details.quantity is not None
            assert details.price is not None
            self._exchange.cancel_order(symbol, details.order_id)
            return self._exchange.place_limit_order(
                symbol, details.side.value, details.quantity, details.price,
            )

        assert details.quantity is not None
        side = action.value  # "BUY" o "SELL"

        if proposal.order_type is OrderType.MARKET:
            return self._exchange.place_market_order(
                symbol, side, details.quantity,
            )

        assert details.price is not None
        return self._exchange.place_limit_order(
            symbol, side, details.quantity, details.price,
        )
