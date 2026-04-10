from __future__ import annotations

import dataclasses
import logging
from typing import Any

from src.agents.base_agent import BaseAgent, unwrap_llm_response
from src.core.contracts import (
    MarketAnalysis,
    MarketAnalystInput,
    MarketBias,
    SuggestedAction,
)
from src.integrations.llm_interfaces.base_llm_interface import BaseLlmInterface


class MarketAnalystAgent(BaseAgent[MarketAnalystInput, MarketAnalysis]):
    def __init__(self, llm: BaseLlmInterface) -> None:
        super().__init__(name="market_analyst", prompt_name="market_analyst.md")
        self._llm = llm
        self._logger = logging.getLogger(f"mdk_crypto_trading.{self.name}")

    def run(self, agent_input: MarketAnalystInput) -> MarketAnalysis:
        system_prompt = self.prompt_path.read_text(encoding="utf-8")
        user_payload = dataclasses.asdict(agent_input.market_data)

        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                response = self._llm.generate_json(system_prompt, user_payload)
                self._logger.debug("Risposta raw LLM: %s", response)
                return _parse_market_analysis(response)
            except (ValueError, KeyError, RuntimeError) as exc:
                self._logger.warning(
                    "Tentativo %d/%d — parsing fallito: %s",
                    attempt, max_attempts, exc,
                )
                if attempt == max_attempts:
                    raise


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
        key_factors=data.get("key_factors", []),
        risk_notes=data.get("risk_notes", []),
        suggested_action=SuggestedAction(
            data.get("suggested_action", "NO_TRADE_BIAS")
        ),
    )
