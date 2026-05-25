from __future__ import annotations

import dataclasses
import math
from typing import Any

from src.agents.base_agent import BaseLlmAgent, unwrap_llm_response
from src.core.contracts import (
    DecisionMakerInput,
    OrderSide,
    OrderType,
    TradeAction,
    TradeProposal,
    TradeProposalDetails,
)
from src.integrations.llm_interfaces.base_llm_interface import BaseLlmInterface


class DecisionMakerAgent(BaseLlmAgent[DecisionMakerInput, TradeProposal]):
    def __init__(self, llm: BaseLlmInterface) -> None:
        super().__init__(
            name="decision_maker",
            prompt_name="decision_maker.md",
            llm=llm,
        )

    def _build_user_payload(self, agent_input: DecisionMakerInput) -> dict[str, Any]:
        return {
            "portfolio": dataclasses.asdict(agent_input.portfolio),
            "market_analysis": dataclasses.asdict(agent_input.market_analysis),
            "constraints": dataclasses.asdict(agent_input.constraints),
            "mandate": dataclasses.asdict(agent_input.mandate),
            "decision_memory": agent_input.decision_memory,
            "performance_summary": agent_input.performance_summary,
            "recent_performance": agent_input.recent_performance,
            "latest_performance_review": agent_input.latest_performance_review,
            "current_price": agent_input.current_price,
            "oco_review_required": agent_input.oco_review_required,
        }

    def _parse_response(self, data: Any) -> TradeProposal:
        return _parse_trade_proposal(data)


def _parse_trade_proposal(data: Any) -> TradeProposal:
    """Valida e converte la risposta JSON del LLM in TradeProposal."""
    data = unwrap_llm_response(data)
    required = ("action", "order_type", "confidence", "reason")
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Campi mancanti nella risposta LLM: {missing}")

    action = TradeAction(data["action"])
    order_type = OrderType(data["order_type"])
    confidence = _validate_confidence(float(data["confidence"]))
    reason = str(data["reason"])
    raw_details: dict[str, Any] = data.get("details", {})

    if action is TradeAction.HOLD:
        order_type = OrderType.NONE
        details = TradeProposalDetails()
    elif action is TradeAction.CANCEL_AND_REPLACE_ORDER:
        details = TradeProposalDetails(
            quantity=_validate_finite_positive(float(raw_details["quantity"]), "quantity"),
            price=_validate_finite_positive(float(raw_details["price"]), "price"),
            order_id=str(raw_details["order_id"]),
            side=OrderSide(raw_details["side"]),
        )
    elif action is TradeAction.SELL_OCO:
        details = TradeProposalDetails(
            quantity=_validate_finite_positive(float(raw_details["quantity"]), "quantity"),
            price=_validate_finite_positive(float(raw_details["price"]), "price"),
            sl_stop_price=_validate_finite_positive(
                float(raw_details["sl_stop_price"]), "sl_stop_price"
            ),
        )
    else:
        # BUY o SELL
        details = TradeProposalDetails(
            quantity=_validate_finite_positive(float(raw_details["quantity"]), "quantity"),
            price=(
                _validate_finite_positive(float(raw_details["price"]), "price")
                if "price" in raw_details
                else None
            ),
        )

    return TradeProposal(
        action=action,
        order_type=order_type,
        confidence=confidence,
        reason=reason,
        details=details,
    )


def _validate_finite_positive(value: float, field_name: str) -> float:
    """Verifica che il valore sia un numero finito e positivo."""
    if not math.isfinite(value):
        raise ValueError(f"Campo '{field_name}' non finito: {value}")
    if value <= 0:
        raise ValueError(f"Campo '{field_name}' deve essere > 0, ricevuto: {value}")
    return value


def _validate_confidence(value: float) -> float:
    """Verifica che la confidence sia nel range [0.0, 1.0]."""
    if not math.isfinite(value):
        raise ValueError(f"Campo 'confidence' non finito: {value}")
    if not (0.0 <= value <= 1.0):
        raise ValueError(f"Campo 'confidence' fuori range [0, 1]: {value}")
    return value
