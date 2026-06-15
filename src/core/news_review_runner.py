from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.agents.news_reviewer import NewsReviewerAgent
from src.core.contracts import NewsDigest, NewsReviewerInput, NewsSentiment
from src.integrations.news.base_news_client import BaseNewsClient
from src.utils.news_report import write_news_report


class NewsReviewRunner:
    """Orchestra la review periodica delle notizie tramite il NewsReviewerAgent.

    Usa il gate basato sui file di report (stessa filosofia del
    ``PerformanceReviewRunner``): il ciclo sopravvive ai restart perché lo
    stato è scritto su disco, non in memoria.

    Intervallo di default: 12 ore. Se l'ultimo report è più recente
    dell'intervallo, ``maybe_run`` esce immediatamente senza chiamare il client.
    """

    def __init__(
        self,
        symbol: str,
        news_client: BaseNewsClient,
        news_reviewer: NewsReviewerAgent,
        reports_dir: Path,
        logger: logging.Logger,
        interval_hours: int = 12,
        lookback_hours: int = 12,
    ) -> None:
        self._symbol = symbol
        self._news_client = news_client
        self._news_reviewer = news_reviewer
        self._reports_dir = reports_dir
        self._logger = logger
        self._interval_hours = interval_hours
        self._lookback_hours = lookback_hours

    def maybe_run(self, now: datetime | None = None) -> None:
        """Esegue la review se l'intervallo è trascorso dall'ultimo report.

        Non bloccante: qualsiasi eccezione viene loggata come warning e il
        ciclo di trading continua normalmente. Le news non fermano mai il trading.
        """
        reference = now or datetime.now(timezone.utc)
        latest = self._latest_report_time()
        if latest is not None:
            elapsed = reference - latest
            if elapsed < timedelta(hours=self._interval_hours):
                return

        try:
            articles = self._news_client.get_recent_news()

            if not articles:
                digest = NewsDigest(
                    overall_sentiment=NewsSentiment.NEUTRAL,
                    summary="Nessuna notizia rilevante nelle ultime ore.",
                    key_events=[],
                    risk_flags=[],
                )
            else:
                digest = self._news_reviewer.run(
                    NewsReviewerInput(
                        symbol=self._symbol,
                        articles=articles,
                        hours_analyzed=self._lookback_hours,
                    )
                )

            write_news_report(
                symbol=self._symbol,
                digest=digest,
                hours_analyzed=self._lookback_hours,
                reports_dir=self._reports_dir,
                now=reference,
            )
            self._logger.info(
                "News Reviewer → %s (%d articoli analizzati)",
                digest.overall_sentiment.value,
                len(articles),
            )
        except Exception as exc:
            self._logger.warning(
                "News Reviewer fallito (ciclo continua): %s", exc,
            )

    def load_latest_review(self) -> str:
        """Ritorna il contenuto dell'ultimo report news, o stringa vuota."""
        if not self._reports_dir.exists():
            return ""
        files = sorted(self._reports_dir.glob("*.md"))
        if not files:
            return ""
        try:
            return files[-1].read_text(encoding="utf-8")
        except OSError:
            return ""

    def _latest_report_time(self) -> datetime | None:
        """Ricava il timestamp UTC dall'ultimo file ``YYYY-MM-DD_HH-MM.md``.

        Ritorna ``None`` se la cartella è vuota o il nome non è parsabile.
        """
        if not self._reports_dir.exists():
            return None
        files = sorted(self._reports_dir.glob("*.md"))
        if not files:
            return None
        stem = files[-1].stem  # e.g. "2026-06-15_13-30"
        try:
            return datetime.strptime(stem, "%Y-%m-%d_%H-%M").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            return None
