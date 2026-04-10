from __future__ import annotations

import dataclasses
import logging
from typing import Any

from src.agents.base_agent import BaseAgent, unwrap_llm_response
from src.core.contracts import (
    DecisionMakerInput,
    OrderSide,
    OrderType,
    TradeAction,
    TradeProposal,
    TradeProposalDetails,
)
from src.integrations.llm_interfaces.base_llm_interface import BaseLlmInterface


class DecisionMakerAgent(BaseAgent[DecisionMakerInput, TradeProposal]):
    def __init__(self, llm: BaseLlmInterface) -> None:
        super().__init__(name="decision_maker", prompt_name="decision_maker.md")
        self._llm = llm
        self._logger = logging.getLogger(f"mdk_crypto_trading.{self.name}")

    def run(self, agent_input: DecisionMakerInput) -> TradeProposal:
        system_prompt = self.prompt_path.read_text(encoding="utf-8")

        user_payload: dict[str, Any] = {
            "portfolio": dataclasses.asdict(agent_input.portfolio),
            "market_analysis": dataclasses.asdict(agent_input.market_analysis),
            "constraints": dataclasses.asdict(agent_input.constraints),
            "ia_memory": agent_input.ia_memory,
            "performance_summary": agent_input.performance_summary,
            "recent_performance": agent_input.recent_performance,
        }

        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                response = self._llm.generate_json(system_prompt, user_payload)
                self._logger.debug("Risposta raw LLM: %s", response)
                return _parse_trade_proposal(response)
            except (ValueError, KeyError, RuntimeError) as exc:
                self._logger.warning(
                    "Tentativo %d/%d — parsing fallito: %s",
                    attempt, max_attempts, exc,
                )
                if attempt == max_attempts:
                    raise


def _parse_trade_proposal(data: Any) -> TradeProposal:
    """Valida e converte la risposta JSON del LLM in TradeProposal."""
    data = unwrap_llm_response(data)
    required = ("action", "order_type", "confidence", "reason")
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Campi mancanti nella risposta LLM: {missing}")

    action = TradeAction(data["action"])
    order_type = OrderType(data["order_type"])
    confidence = float(data["confidence"])
    reason = str(data["reason"])
    raw_details: dict[str, Any] = data.get("details", {})

    if action is TradeAction.HOLD:
        details = TradeProposalDetails()
    elif action is TradeAction.CANCEL_AND_REPLACE_ORDER:
        details = TradeProposalDetails(
            quantity=float(raw_details["quantity"]),
            price=float(raw_details["price"]),
            order_id=str(raw_details["order_id"]),
            side=OrderSide(raw_details["side"]),
        )
    else:
        # BUY o SELL
        details = TradeProposalDetails(
            quantity=float(raw_details["quantity"]),
            price=float(raw_details["price"]) if "price" in raw_details else None,
        )

    return TradeProposal(
        action=action,
        order_type=order_type,
        confidence=confidence,
        reason=reason,
        details=details,
    )
