from __future__ import annotations

import dataclasses
from typing import Any

from src.agents.base_agent import BaseLlmAgent, ensure_list_of_str, unwrap_llm_response
from src.core.contracts import NewsDigest, NewsReviewerInput, NewsSentiment
from src.integrations.llm_interfaces.base_llm_interface import BaseLlmInterface


class NewsReviewerAgent(BaseLlmAgent[NewsReviewerInput, NewsDigest]):
    """Agente consultivo che trasforma articoli di notizie in un digest strutturato.

    Non partecipa alla catena decisionale: riceve la lista di ``NewsArticle``
    prodotta dall'``AlphaVantageClient`` e produce un ``NewsDigest``
    (overall_sentiment, summary, key_events, risk_flags) che il Decision Maker
    potrà usare come contesto aggiuntivo nelle fasi successive.
    """

    def __init__(self, llm: BaseLlmInterface) -> None:
        super().__init__(
            name="news_reviewer",
            prompt_name="news_reviewer.md",
            llm=llm,
        )

    def _build_user_payload(self, agent_input: NewsReviewerInput) -> dict[str, Any]:
        articles_without_url = [
            {k: v for k, v in dataclasses.asdict(a).items() if k != "url"}
            for a in agent_input.articles
        ]
        return {
            "symbol": agent_input.symbol,
            "hours_analyzed": agent_input.hours_analyzed,
            "article_count": len(agent_input.articles),
            "articles": articles_without_url,
        }

    def _parse_response(self, data: Any) -> NewsDigest:
        return _parse_news_digest(data)


def _parse_news_digest(data: Any) -> NewsDigest:
    """Valida e converte la risposta JSON del LLM in ``NewsDigest``."""
    data = unwrap_llm_response(data)
    required = ("overall_sentiment", "summary")
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Campi mancanti nella risposta LLM: {missing}")

    return NewsDigest(
        overall_sentiment=NewsSentiment(data["overall_sentiment"]),
        summary=str(data["summary"]),
        key_events=ensure_list_of_str(data.get("key_events", [])),
        risk_flags=ensure_list_of_str(data.get("risk_flags", [])),
    )
