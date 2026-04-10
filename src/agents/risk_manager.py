from __future__ import annotations

import dataclasses
import logging
from typing import Any

from src.agents.base_agent import BaseAgent, unwrap_llm_response
from src.core.contracts import (
    RiskAssessment,
    RiskDecision,
    RiskManagerInput,
)
from src.integrations.llm_interfaces.base_llm_interface import BaseLlmInterface


class RiskManagerAgent(BaseAgent[RiskManagerInput, RiskAssessment]):
    def __init__(self, llm: BaseLlmInterface) -> None:
        super().__init__(name="risk_manager", prompt_name="risk_manager.md")
        self._llm = llm
        self._logger = logging.getLogger(f"mdk_crypto_trading.{self.name}")

    def run(self, agent_input: RiskManagerInput) -> RiskAssessment:
        system_prompt = self.prompt_path.read_text(encoding="utf-8")

        market_analysis_subset = {
            "market_bias": agent_input.market_analysis.market_bias.value,
            "summary": agent_input.market_analysis.summary,
            "risk_notes": agent_input.market_analysis.risk_notes,
        }

        user_payload: dict[str, Any] = {
            "proposal": dataclasses.asdict(agent_input.proposal),
            "portfolio": dataclasses.asdict(agent_input.portfolio),
            "market_analysis": market_analysis_subset,
            "constraints": dataclasses.asdict(agent_input.constraints),
            "current_price": agent_input.current_price,
        }

        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                response = self._llm.generate_json(system_prompt, user_payload)
                self._logger.debug("Risposta raw LLM: %s", response)
                return _parse_risk_assessment(response)
            except (ValueError, KeyError, RuntimeError) as exc:
                self._logger.warning(
                    "Tentativo %d/%d — parsing fallito: %s",
                    attempt, max_attempts, exc,
                )
                if attempt == max_attempts:
                    raise


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
        checks=data.get("checks", []),
        required_changes=data.get("required_changes", []),
    )
