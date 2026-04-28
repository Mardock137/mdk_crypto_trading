from __future__ import annotations

import dataclasses
from typing import Any

from src.agents.base_agent import BaseAgent, ensure_list_of_str, unwrap_llm_response
from src.core.contracts import (
    MandateAdherence,
    PerformanceReview,
    PerformanceReviewerInput,
)
from src.integrations.llm_interfaces.base_llm_interface import BaseLlmInterface


class PerformanceReviewerAgent(
    BaseAgent[PerformanceReviewerInput, PerformanceReview]
):
    """Agente consultivo che produce un giudizio giornaliero sulle performance.

    Non partecipa alla catena decisionale: riceve statistiche pre-calcolate
    e mandato, produce summary + aderenza + suggerimenti che alimentano il
    Decision Maker nei cicli successivi.
    """

    def __init__(self, llm: BaseLlmInterface) -> None:
        super().__init__(name="performance_reviewer", prompt_name="performance_reviewer.md")
        self._llm = llm

    def run(self, agent_input: PerformanceReviewerInput) -> PerformanceReview:
        if self.prompt_path is None:
            raise RuntimeError(f"Prompt path non configurato per l'agente '{self.name}'.")
        system_prompt = self.prompt_path.read_text(encoding="utf-8")

        user_payload: dict[str, Any] = {
            "symbol": agent_input.symbol,
            "days_analyzed": agent_input.days_analyzed,
            "mandate": dataclasses.asdict(agent_input.mandate),
            "stats": dataclasses.asdict(agent_input.stats),
        }

        return self._call_llm_with_retry(
            self._llm, system_prompt, user_payload, _parse_performance_review,
        )


def _parse_performance_review(data: Any) -> PerformanceReview:
    """Valida e converte la risposta JSON del LLM in ``PerformanceReview``."""
    data = unwrap_llm_response(data)
    required = ("summary", "mandate_adherence")
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Campi mancanti nella risposta LLM: {missing}")

    return PerformanceReview(
        summary=str(data["summary"]),
        mandate_adherence=MandateAdherence(data["mandate_adherence"]),
        suggestions=ensure_list_of_str(data.get("suggestions", [])),
    )
