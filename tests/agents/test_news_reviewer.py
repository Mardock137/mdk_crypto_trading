"""Test per NewsReviewerAgent e _parse_news_digest."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from src.agents.news_reviewer import NewsReviewerAgent, _parse_news_digest
from src.core.contracts import NewsArticle, NewsDigest, NewsReviewerInput, NewsSentiment


# ---------- helpers ----------


def _make_article(**overrides: Any) -> NewsArticle:
    defaults: dict[str, Any] = dict(
        title="Bitcoin ETF inflows record",
        url="https://example.com/btc-etf",
        source="Reuters",
        summary="BTC ETF registra inflows record di 500M$.",
        time_published="20240601T120000",
        overall_sentiment_score=0.45,
        overall_sentiment_label="Bullish",
        btc_sentiment_score=0.5,
        btc_relevance=0.9,
    )
    defaults.update(overrides)
    return NewsArticle(**defaults)


def _make_input(articles: list[NewsArticle] | None = None) -> NewsReviewerInput:
    return NewsReviewerInput(
        symbol="BTCUSDC",
        articles=articles if articles is not None else [_make_article()],
        hours_analyzed=12,
    )


# ---------- parsing dei tre valori di overall_sentiment ----------


def test_parse_bullish() -> None:
    data = {
        "overall_sentiment": "BULLISH",
        "summary": "Flusso news positivo.",
        "key_events": ["ETF inflows record"],
        "risk_flags": [],
    }
    result = _parse_news_digest(data)

    assert result.overall_sentiment is NewsSentiment.BULLISH
    assert result.summary == "Flusso news positivo."
    assert result.key_events == ["ETF inflows record"]
    assert result.risk_flags == []


def test_parse_bearish() -> None:
    data = {
        "overall_sentiment": "BEARISH",
        "summary": "Pressione ribassista.",
        "key_events": ["SEC multa exchange"],
        "risk_flags": ["Possibile contagio sentiment"],
    }
    result = _parse_news_digest(data)

    assert result.overall_sentiment is NewsSentiment.BEARISH
    assert result.risk_flags == ["Possibile contagio sentiment"]


def test_parse_neutral() -> None:
    data = {
        "overall_sentiment": "NEUTRAL",
        "summary": "Nessun evento di rilievo nelle ultime 12 ore.",
    }
    result = _parse_news_digest(data)

    assert result.overall_sentiment is NewsSentiment.NEUTRAL
    assert result.key_events == []
    assert result.risk_flags == []


# ---------- campi mancanti ----------


def test_parse_missing_summary_raises() -> None:
    with pytest.raises(ValueError, match="Campi mancanti"):
        _parse_news_digest({"overall_sentiment": "BULLISH"})


def test_parse_missing_overall_sentiment_raises() -> None:
    with pytest.raises(ValueError, match="Campi mancanti"):
        _parse_news_digest({"summary": "x"})


def test_parse_empty_dict_raises() -> None:
    with pytest.raises(ValueError, match="dict vuoto"):
        _parse_news_digest({})


# ---------- normalizzazione liste ----------


def test_parse_key_events_as_string_normalized_to_list() -> None:
    data = {
        "overall_sentiment": "BULLISH",
        "summary": "x",
        "key_events": "Solo un evento chiave",
    }
    result = _parse_news_digest(data)

    assert result.key_events == ["Solo un evento chiave"]


def test_parse_risk_flags_as_string_normalized_to_list() -> None:
    data = {
        "overall_sentiment": "NEUTRAL",
        "summary": "x",
        "risk_flags": "Un solo risk flag",
    }
    result = _parse_news_digest(data)

    assert result.risk_flags == ["Un solo risk flag"]


# ---------- agent run ----------


def test_agent_run_calls_llm_and_parses_response() -> None:
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "overall_sentiment": "BULLISH",
        "summary": "Flusso news positivo.",
        "key_events": ["ETF inflows"],
        "risk_flags": [],
    }

    agent = NewsReviewerAgent(llm=mock_llm)
    mock_prompt = MagicMock()
    mock_prompt.read_text.return_value = "system prompt"
    with patch("src.agents.base_agent.time.sleep"):
        with patch.object(
            type(agent), "prompt_path",
            new_callable=PropertyMock, return_value=mock_prompt,
        ):
            result = agent.run(_make_input())

    assert isinstance(result, NewsDigest)
    assert result.overall_sentiment is NewsSentiment.BULLISH
    mock_llm.generate_json.assert_called_once()

    _, payload = mock_llm.generate_json.call_args.args
    assert payload["symbol"] == "BTCUSDC"
    assert payload["hours_analyzed"] == 12
    assert payload["article_count"] == 1
    assert isinstance(payload["articles"], list)
    assert payload["articles"][0]["title"] == "Bitcoin ETF inflows record"
