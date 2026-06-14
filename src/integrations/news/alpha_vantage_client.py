from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.core.contracts import NewsArticle
from src.core.exceptions import NewsError
from src.integrations.news.base_news_client import BaseNewsClient

_AV_URL = "https://www.alphavantage.co/query"

logger = logging.getLogger(__name__)


def _is_retryable_news(exc: BaseException) -> bool:
    """Ritorna True per errori di rete/HTTP transitori degni di retry."""
    if isinstance(exc, requests.exceptions.ConnectionError):
        return True
    if isinstance(exc, requests.exceptions.Timeout):
        return True
    if isinstance(exc, requests.exceptions.HTTPError):
        resp = exc.response
        return resp is not None and resp.status_code >= 500
    return False


_news_retry = retry(
    retry=retry_if_exception(_is_retryable_news),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    reraise=True,
)


class AlphaVantageClient(BaseNewsClient):
    """Client Alpha Vantage per il download di notizie crypto con sentiment.

    Implementa ``BaseNewsClient``. Effettua chiamate HTTP all'endpoint
    ``NEWS_SENTIMENT`` con retry automatico su errori transienti di rete.
    Gli errori operativi (chiave esaurita, rate limit, parsing) vengono
    incapsulati in ``NewsError``.
    """

    def __init__(
        self,
        api_key: str,
        *,
        topics: str = "blockchain",
        tickers: str = "",
        lookback_hours: int = 12,
        max_articles: int = 50,
        sort: str = "LATEST",
    ) -> None:
        self._api_key = api_key
        self._topics = topics
        self._tickers = tickers
        self._lookback_hours = lookback_hours
        self._max_articles = max_articles
        self._sort = sort

    def get_recent_news(self) -> list[NewsArticle]:
        """Scarica le notizie recenti e le restituisce come lista di NewsArticle.

        Solleva ``NewsError`` in caso di errore HTTP, timeout, quirk Alpha Vantage
        (risposta 200 con campo ``Information``/``Note``/``Error Message``) o
        errore di parsing.
        """
        try:
            data = self._fetch_with_retry()
        except NewsError:
            raise
        except Exception as exc:
            raise NewsError(f"Errore durante il fetch delle notizie: {exc}") from exc

        for key in ("Information", "Note", "Error Message"):
            if key in data:
                raise NewsError(f"Alpha Vantage: {data[key]}")

        return self._parse_feed(data.get("feed") or [])

    @_news_retry
    def _fetch_with_retry(self) -> dict[str, Any]:
        time_from = (
            datetime.now(timezone.utc) - timedelta(hours=self._lookback_hours)
        ).strftime("%Y%m%dT%H%M")

        params: dict[str, Any] = {
            "function": "NEWS_SENTIMENT",
            "apikey": self._api_key,
            "topics": self._topics,
            "time_from": time_from,
            "limit": self._max_articles,
            "sort": self._sort,
        }
        if self._tickers:
            params["tickers"] = self._tickers

        resp = requests.get(_AV_URL, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _parse_feed(self, feed: list[dict[str, Any]]) -> list[NewsArticle]:
        articles: list[NewsArticle] = []
        for item in feed:
            try:
                articles.append(self._parse_article(item))
            except Exception as exc:
                logger.warning("Articolo ignorato per errore di parsing: %s", exc)
        return articles

    def _parse_article(self, item: dict[str, Any]) -> NewsArticle:
        btc_score: float | None = None
        btc_relevance: float | None = None
        for ts in item.get("ticker_sentiment", []):
            if ts.get("ticker") == "CRYPTO:BTC":
                try:
                    btc_score = float(ts["ticker_sentiment_score"])
                except (KeyError, TypeError, ValueError):
                    pass
                try:
                    btc_relevance = float(ts["relevance_score"])
                except (KeyError, TypeError, ValueError):
                    pass
                break

        overall_score: float | None = None
        raw_score = item.get("overall_sentiment_score")
        if raw_score is not None:
            try:
                overall_score = float(raw_score)
            except (TypeError, ValueError):
                pass

        raw_label = item.get("overall_sentiment_label")
        return NewsArticle(
            title=str(item.get("title", "")),
            url=str(item.get("url", "")),
            source=str(item.get("source", "")),
            summary=str(item.get("summary", "")),
            time_published=str(item.get("time_published", "")),
            overall_sentiment_score=overall_score,
            overall_sentiment_label=str(raw_label) if raw_label is not None else None,
            btc_sentiment_score=btc_score,
            btc_relevance=btc_relevance,
        )
