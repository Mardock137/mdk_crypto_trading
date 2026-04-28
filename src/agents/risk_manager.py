from __future__ import annotations

import dataclasses
from typing import Any

from src.agents.base_agent import BaseLlmAgent, ensure_list_of_str, unwrap_llm_response
from src.core.contracts import (
    RiskAssessment,
    RiskDecision,
    RiskManagerInput,
)
from src.integrations.llm_interfaces.base_llm_interface import BaseLlmInterface


class RiskManagerAgent(BaseLlmAgent[RiskManagerInput, RiskAssessment]):
    def __init__(self, llm: BaseLlmInterface) -> None:
        super().__init__(
            name="risk_manager",
            prompt_name="risk_manager.md",
            llm=llm,
        )

    def _build_user_payload(self, agent_input: RiskManagerInput) -> dict[str, Any]:
        market_analysis_subset = {
            "market_bias": agent_input.market_analysis.market_bias.value,
            "summary": agent_input.market_analysis.summary,
            "risk_notes": agent_input.market_analysis.risk_notes,
        }
        return {
            "proposal": dataclasses.asdict(agent_input.proposal),
            "portfolio": dataclasses.asdict(agent_input.portfolio),
            "market_analysis": market_analysis_subset,
            "constraints": dataclasses.asdict(agent_input.constraints),
            "current_price": agent_input.current_price,
        }

    def _parse_response(self, data: Any) -> RiskAssessment:
        return _parse_risk_assessment(data)


def _parse_risk_assessment(data: Any) -> RiskAssessment:
    """Valida e converte la risposta JSON del LLM in RiskAssessment."""
    data = unwrap_llm_response(data)
    required = ("risk_decision", "confidence", "reason")
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Campi mancanti nella risposta LLM: {missing}")

    return RiskAssessment(
        risk_decision=RiskDecision(data["risk_decision"]),
        confidence=float(data["confidence"]),
        reason=str(data["reason"]),
        checks=ensure_list_of_str(data.get("checks", [])),
        required_changes=ensure_list_of_str(data.get("required_changes", [])),
    )
