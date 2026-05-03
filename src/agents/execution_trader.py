from __future__ import annotations

import logging
import math
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

        guardrail_block = self._validate_guardrails(agent_input)
        if guardrail_block is not None:
            return guardrail_block

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

    def _validate_guardrails(self, agent_input: ExecutionInput) -> ExecutionReport | None:
        """Controlla i guardrail deterministici prima di eseguire un ordine.

        Ritorna un ``ExecutionReport`` di blocco se un guardrail fallisce,
        ``None`` se tutti i controlli passano.
        """
        proposal = agent_input.proposal
        details = proposal.details
        portfolio = agent_input.portfolio
        mandate = agent_input.mandate
        max_notional = agent_input.max_order_notional_usdc

        # 1. Validazione numerica difensiva
        qty = details.quantity
        price = details.price
        if qty is not None and (not math.isfinite(qty) or qty <= 0):
            return ExecutionReport(
                execution_status=ExecutionStatus.NOT_EXECUTED,
                executed_action=proposal.action,
                order_type=proposal.order_type,
                reason=f"Guardrail: quantity non valida ({qty})",
            )
        if price is not None and (not math.isfinite(price) or price <= 0):
            return ExecutionReport(
                execution_status=ExecutionStatus.NOT_EXECUTED,
                executed_action=proposal.action,
                order_type=proposal.order_type,
                reason=f"Guardrail: price non valido ({price})",
            )

        # 2. Cap notional massimo per ordine
        if qty is not None:
            reference_price = price if price is not None else agent_input.current_price
            if reference_price is None:
                return ExecutionReport(
                    execution_status=ExecutionStatus.NOT_EXECUTED,
                    executed_action=proposal.action,
                    order_type=proposal.order_type,
                    reason=(
                        "Guardrail: nessun reference price disponibile per "
                        "calcolare il notional, ordine bloccato"
                    ),
                )

            notional = qty * reference_price
            if notional > max_notional:
                return ExecutionReport(
                    execution_status=ExecutionStatus.NOT_EXECUTED,
                    executed_action=proposal.action,
                    order_type=proposal.order_type,
                    reason=(
                        f"Guardrail: notional {notional:.2f} USDC supera il cap "
                        f"{max_notional:.2f} USDC"
                    ),
                )

            # 3. Cap percentuale sul portafoglio
            if portfolio.usdc_value > 0:
                pct = (notional / portfolio.usdc_value) * 100
                if pct > mandate.max_position_pct:
                    return ExecutionReport(
                        execution_status=ExecutionStatus.NOT_EXECUTED,
                        executed_action=proposal.action,
                        order_type=proposal.order_type,
                        reason=(
                            f"Guardrail: notional {notional:.2f} USDC rappresenta "
                            f"{pct:.1f}% del portafoglio, oltre il limite "
                            f"{mandate.max_position_pct:.1f}%"
                        ),
                    )

        # 4. Verifica order_id per CANCEL_AND_REPLACE
        if proposal.action is TradeAction.CANCEL_AND_REPLACE_ORDER:
            order_id = details.order_id
            known_ids = {
                str(o.get("orderId", "")) for o in portfolio.open_orders
            } | {
                str(o.get("clientOrderId", "")) for o in portfolio.open_orders
            }
            known_ids.discard("")
            if order_id not in known_ids:
                return ExecutionReport(
                    execution_status=ExecutionStatus.NOT_EXECUTED,
                    executed_action=proposal.action,
                    order_type=proposal.order_type,
                    reason=(
                        f"Guardrail: order_id '{order_id}' non trovato negli "
                        "ordini aperti del portafoglio"
                    ),
                )

        # 5. Guardrail specifici per SELL_OCO
        if proposal.action is TradeAction.SELL_OCO:
            sl_stop = details.sl_stop_price
            tp = details.price
            sell_qty = details.quantity

            if tp is None or sl_stop is None or sell_qty is None:
                return ExecutionReport(
                    execution_status=ExecutionStatus.NOT_EXECUTED,
                    executed_action=proposal.action,
                    order_type=proposal.order_type,
                    reason=(
                        "Guardrail SELL_OCO: price (TP), sl_stop_price e quantity "
                        "sono tutti obbligatori"
                    ),
                )

            current_price = agent_input.current_price
            if current_price is None:
                return ExecutionReport(
                    execution_status=ExecutionStatus.NOT_EXECUTED,
                    executed_action=proposal.action,
                    order_type=proposal.order_type,
                    reason=(
                        "Guardrail SELL_OCO: current_price non disponibile, "
                        "impossibile verificare l'ordinamento dei prezzi"
                    ),
                )

            if not (tp > current_price > sl_stop):
                return ExecutionReport(
                    execution_status=ExecutionStatus.NOT_EXECUTED,
                    executed_action=proposal.action,
                    order_type=proposal.order_type,
                    reason=(
                        f"Guardrail SELL_OCO: ordinamento prezzi non valido — "
                        f"atteso tp ({tp}) > current ({current_price}) > sl_stop ({sl_stop})"
                    ),
                )

            if sell_qty > portfolio.portfolio_qty_free:
                return ExecutionReport(
                    execution_status=ExecutionStatus.NOT_EXECUTED,
                    executed_action=proposal.action,
                    order_type=proposal.order_type,
                    reason=(
                        f"Guardrail SELL_OCO: quantity {sell_qty} supera "
                        f"portfolio_qty_free {portfolio.portfolio_qty_free}"
                    ),
                )

        return None

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

        if action is TradeAction.SELL_OCO:
            if details.quantity is None:
                raise ValueError("quantity is required for SELL_OCO.")
            if details.price is None:
                raise ValueError("price (tp_price) is required for SELL_OCO.")
            if details.sl_stop_price is None:
                raise ValueError("sl_stop_price is required for SELL_OCO.")
            return self._exchange.place_oco_sell(
                symbol, details.quantity, details.price, details.sl_stop_price,
            )

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
