"""Test per AlphaVantageClient (requests.get mockato)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.core.contracts import NewsArticle
from src.core.exceptions import NewsError
from src.integrations.news.alpha_vantage_client import AlphaVantageClient


# ---------- helpers ----------


def _make_client(**overrides: Any) -> AlphaVantageClient:
    defaults: dict[str, Any] = dict(
        api_key="test-key",
        topics="blockchain",
        tickers="",
        lookback_hours=12,
        max_articles=50,
        sort="LATEST",
    )
    defaults.update(overrides)
    return AlphaVantageClient(**defaults)


def _feed_item(**overrides: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "title": "Bitcoin surges",
        "url": "https://example.com/btc",
        "source": "Reuters",
        "summary": "BTC is up 10%",
        "time_published": "20240101T120000",
        "overall_sentiment_score": "0.35",
        "overall_sentiment_label": "Bullish",
        "ticker_sentiment": [
            {
                "ticker": "CRYPTO:BTC",
                "ticker_sentiment_score": "0.42",
                "relevance_score": "0.9",
            }
        ],
    }
    item.update(overrides)
    return item


def _mock_ok(json_data: dict[str, Any]) -> MagicMock:
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.raise_for_status.return_value = None
    return mock


# ---------- parsing corretto ----------


def test_returns_list_of_news_articles() -> None:
    client = _make_client()
    mock_resp = _mock_ok({"feed": [_feed_item(), _feed_item(title="ETH news")]})

    with patch("requests.get", return_value=mock_resp):
        result = client.get_recent_news()

    assert len(result) == 2
    assert all(isinstance(a, NewsArticle) for a in result)


def test_parses_article_fields_correctly() -> None:
    client = _make_client()
    mock_resp = _mock_ok({"feed": [_feed_item()]})

    with patch("requests.get", return_value=mock_resp):
        articles = client.get_recent_news()

    art = articles[0]
    assert art.title == "Bitcoin surges"
    assert art.url == "https://example.com/btc"
    assert art.source == "Reuters"
    assert art.summary == "BTC is up 10%"
    assert art.time_published == "20240101T120000"
    assert art.overall_sentiment_label == "Bullish"
    assert art.overall_sentiment_score == pytest.approx(0.35)


def test_extracts_btc_sentiment_from_ticker_sentiment() -> None:
    client = _make_client()
    mock_resp = _mock_ok({"feed": [_feed_item()]})

    with patch("requests.get", return_value=mock_resp):
        articles = client.get_recent_news()

    art = articles[0]
    assert art.btc_sentiment_score == pytest.approx(0.42)
    assert art.btc_relevance == pytest.approx(0.9)


def test_btc_sentiment_is_none_when_not_present() -> None:
    item = _feed_item()
    item["ticker_sentiment"] = []
    client = _make_client()

    with patch("requests.get", return_value=_mock_ok({"feed": [item]})):
        articles = client.get_recent_news()

    assert articles[0].btc_sentiment_score is None
    assert articles[0].btc_relevance is None


def test_empty_feed_returns_empty_list() -> None:
    client = _make_client()

    with patch("requests.get", return_value=_mock_ok({"feed": []})):
        result = client.get_recent_news()

    assert result == []


def test_missing_feed_key_returns_empty_list() -> None:
    client = _make_client()

    with patch("requests.get", return_value=_mock_ok({"items": "0"})):
        result = client.get_recent_news()

    assert result == []


# ---------- quirk Alpha Vantage ----------


def test_raises_news_error_on_information_key() -> None:
    client = _make_client()
    payload = {"Information": "Thank you for using Alpha Vantage! API rate limit exceeded."}

    with patch("requests.get", return_value=_mock_ok(payload)):
        with pytest.raises(NewsError, match="Alpha Vantage"):
            client.get_recent_news()


def test_raises_news_error_on_note_key() -> None:
    client = _make_client()
    payload = {"Note": "Thank you for using Alpha Vantage! Our standard API call frequency..."}

    with patch("requests.get", return_value=_mock_ok(payload)):
        with pytest.raises(NewsError):
            client.get_recent_news()


def test_raises_news_error_on_error_message_key() -> None:
    client = _make_client()
    payload = {"Error Message": "Invalid API call. Please retry or visit Alpha Vantage."}

    with patch("requests.get", return_value=_mock_ok(payload)):
        with pytest.raises(NewsError):
            client.get_recent_news()


# ---------- errori HTTP / rete ----------


def test_raises_news_error_on_non_retryable_http_error() -> None:
    """Un errore HTTP 403 (non retriable) deve essere convertito in NewsError."""
    client = _make_client()
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    http_error = requests.exceptions.HTTPError(response=mock_resp)
    mock_resp.raise_for_status.side_effect = http_error

    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(NewsError):
            client.get_recent_news()


def test_raises_news_error_after_connection_error_retries() -> None:
    """Dopo aver esaurito i retry su ConnectionError, deve essere sollevato NewsError."""
    client = _make_client()

    with patch(
        "requests.get",
        side_effect=requests.exceptions.ConnectionError("network unreachable"),
    ):
        with pytest.raises(NewsError):
            client.get_recent_news()


# ---------- costruzione dei parametri ----------


def test_builds_params_with_correct_values() -> None:
    client = _make_client(
        topics="blockchain",
        tickers="CRYPTO:BTC",
        lookback_hours=6,
        max_articles=10,
        sort="RELEVANCE",
    )

    with patch("requests.get", return_value=_mock_ok({"feed": []})) as mock_get:
        client.get_recent_news()

    params = mock_get.call_args.kwargs["params"]
    assert params["function"] == "NEWS_SENTIMENT"
    assert params["topics"] == "blockchain"
    assert params["tickers"] == "CRYPTO:BTC"
    assert params["limit"] == 10
    assert params["sort"] == "RELEVANCE"
    assert "time_from" in params


def test_does_not_include_tickers_param_when_empty() -> None:
    client = _make_client(tickers="")

    with patch("requests.get", return_value=_mock_ok({"feed": []})) as mock_get:
        client.get_recent_news()

    params = mock_get.call_args.kwargs["params"]
    assert "tickers" not in params
