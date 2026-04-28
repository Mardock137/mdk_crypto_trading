from __future__ import annotations

import dataclasses
from typing import Any

from src.agents.base_agent import BaseLlmAgent, ensure_list_of_str, unwrap_llm_response
from src.core.contracts import (
    MarketAnalysis,
    MarketAnalystInput,
    MarketBias,
    SuggestedAction,
)
from src.integrations.llm_interfaces.base_llm_interface import BaseLlmInterface


class MarketAnalystAgent(BaseLlmAgent[MarketAnalystInput, MarketAnalysis]):
    def __init__(self, llm: BaseLlmInterface) -> None:
        super().__init__(
            name="market_analyst",
            prompt_name="market_analyst.md",
            llm=llm,
        )

    def _build_user_payload(self, agent_input: MarketAnalystInput) -> dict[str, Any]:
        return dataclasses.asdict(agent_input.market_data)

    def _parse_response(self, data: Any) -> MarketAnalysis:
        return _parse_market_analysis(data)


def _parse_market_analysis(data: Any) -> MarketAnalysis:
    """Valida e converte la risposta JSON del LLM in MarketAnalysis."""
    data = unwrap_llm_response(data)
    required = ("market_bias", "signal_strength", "confidence", "summary")
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Campi mancanti nella risposta LLM: {missing}")

    return MarketAnalysis(
        market_bias=MarketBias(data["market_bias"]),
        signal_strength=float(data["signal_strength"]),
        confidence=float(data["confidence"]),
        summary=str(data["summary"]),
        key_factors=ensure_list_of_str(data.get("key_factors", [])),
        risk_notes=ensure_list_of_str(data.get("risk_notes", [])),
        suggested_action=SuggestedAction(
            data.get("suggested_action", "NO_TRADE_BIAS")
        ),
    )
