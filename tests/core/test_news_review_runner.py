"""Test per src/core/news_review_runner.py."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.contracts import NewsArticle, NewsDigest, NewsSentiment
from src.core.news_review_runner import NewsReviewRunner
from src.core.exceptions import NewsError


# ---------- helpers ----------


_LOGGER = logging.getLogger("test_news_review_runner")

_NOW = datetime(2026, 6, 15, 13, 30, 0, tzinfo=timezone.utc)


def _make_article() -> NewsArticle:
    return NewsArticle(
        title="Bitcoin ETF inflows record",
        url="https://example.com/btc-etf",
        source="Reuters",
        summary="BTC ETF registra inflows record di 500M$.",
        time_published="20260615T120000",
        overall_sentiment_score=0.45,
        overall_sentiment_label="Bullish",
        btc_sentiment_score=0.5,
        btc_relevance=0.9,
    )


def _make_digest(sentiment: NewsSentiment = NewsSentiment.BULLISH) -> NewsDigest:
    return NewsDigest(
        overall_sentiment=sentiment,
        summary="Flusso positivo.",
        key_events=["ETF inflows"],
        risk_flags=[],
    )


def _make_runner(
    tmp_path: Path,
    interval_hours: int = 12,
    lookback_hours: int = 12,
    news_client: MagicMock | None = None,
    news_reviewer: MagicMock | None = None,
) -> NewsReviewRunner:
    client = news_client or MagicMock()
    reviewer = news_reviewer or MagicMock()
    return NewsReviewRunner(
        symbol="BTCUSDC",
        news_client=client,
        news_reviewer=reviewer,
        reports_dir=tmp_path / "news_reports",
        logger=_LOGGER,
        interval_hours=interval_hours,
        lookback_hours=lookback_hours,
    )


def _write_report(reports_dir: Path, filename: str, content: str = "# report") -> Path:
    """Scrive un file di report di prova nella cartella indicata."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


# ---------- gate: nessun report precedente → esegue ----------


def test_maybe_run_executes_when_no_previous_report(tmp_path: Path) -> None:
    """Se non esiste nessun report, deve scaricare news e scrivere il file."""
    mock_client = MagicMock()
    mock_client.get_recent_news.return_value = [_make_article()]
    mock_reviewer = MagicMock()
    mock_reviewer.run.return_value = _make_digest()

    runner = _make_runner(tmp_path, news_client=mock_client, news_reviewer=mock_reviewer)
    runner.maybe_run(now=_NOW)

    mock_client.get_recent_news.assert_called_once()
    mock_reviewer.run.assert_called_once()
    reports_dir = tmp_path / "news_reports"
    assert any(reports_dir.glob("*.md"))


# ---------- gate: report recente → skip ----------


def test_maybe_run_skips_when_report_is_recent(tmp_path: Path) -> None:
    """Se l'ultimo report è stato scritto < interval_hours fa, non fa nulla."""
    reports_dir = tmp_path / "news_reports"
    recent = _NOW - timedelta(hours=6)  # 6h fa, intervallo 12h
    _write_report(reports_dir, recent.strftime("%Y-%m-%d_%H-%M") + ".md")

    mock_client = MagicMock()
    runner = _make_runner(tmp_path, interval_hours=12, news_client=mock_client)
    runner.maybe_run(now=_NOW)

    mock_client.get_recent_news.assert_not_called()


# ---------- gate: report vecchio → esegue ----------


def test_maybe_run_executes_when_report_is_old(tmp_path: Path) -> None:
    """Se l'ultimo report è > interval_hours fa, deve eseguire la review."""
    reports_dir = tmp_path / "news_reports"
    old = _NOW - timedelta(hours=13)  # 13h fa, intervallo 12h
    _write_report(reports_dir, old.strftime("%Y-%m-%d_%H-%M") + ".md")

    mock_client = MagicMock()
    mock_client.get_recent_news.return_value = []
    runner = _make_runner(tmp_path, interval_hours=12, news_client=mock_client)
    runner.maybe_run(now=_NOW)

    mock_client.get_recent_news.assert_called_once()


# ---------- lista articoli vuota → report NEUTRAL, LLM non chiamato ----------


def test_maybe_run_writes_neutral_when_no_articles(tmp_path: Path) -> None:
    """Se non ci sono articoli, deve scrivere NEUTRAL senza chiamare il reviewer."""
    mock_client = MagicMock()
    mock_client.get_recent_news.return_value = []
    mock_reviewer = MagicMock()

    runner = _make_runner(tmp_path, news_client=mock_client, news_reviewer=mock_reviewer)
    runner.maybe_run(now=_NOW)

    mock_reviewer.run.assert_not_called()
    reports_dir = tmp_path / "news_reports"
    files = list(reports_dir.glob("*.md"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")
    assert "NEUTRAL" in content


# ---------- errore del client → non bloccante, warning loggato, nessun report ----------


def test_maybe_run_non_blocking_on_client_error(tmp_path: Path) -> None:
    """Se il client solleva NewsError, nessuna eccezione propagata e nessun report."""
    mock_client = MagicMock()
    mock_client.get_recent_news.side_effect = NewsError("timeout")

    runner = _make_runner(tmp_path, news_client=mock_client)

    with patch.object(_LOGGER, "warning") as mock_warning:
        runner.maybe_run(now=_NOW)

    mock_warning.assert_called_once()
    reports_dir = tmp_path / "news_reports"
    assert not any(reports_dir.glob("*.md")) if reports_dir.exists() else True


def test_maybe_run_non_blocking_on_generic_error(tmp_path: Path) -> None:
    """Qualsiasi eccezione dal reviewer non deve propagarsi al ciclo."""
    mock_client = MagicMock()
    mock_client.get_recent_news.return_value = [_make_article()]
    mock_reviewer = MagicMock()
    mock_reviewer.run.side_effect = RuntimeError("LLM error")

    runner = _make_runner(tmp_path, news_client=mock_client, news_reviewer=mock_reviewer)

    # Non deve sollevare eccezioni
    runner.maybe_run(now=_NOW)


# ---------- load_latest_review ----------


def test_load_latest_review_returns_content(tmp_path: Path) -> None:
    """load_latest_review deve ritornare il contenuto dell'ultimo report."""
    reports_dir = tmp_path / "news_reports"
    _write_report(reports_dir, "2026-06-15_10-00.md", "# report A")
    _write_report(reports_dir, "2026-06-15_12-00.md", "# report B")

    runner = _make_runner(tmp_path)
    result = runner.load_latest_review()

    assert result == "# report B"


def test_load_latest_review_returns_empty_when_no_reports(tmp_path: Path) -> None:
    """load_latest_review deve ritornare stringa vuota se non ci sono report."""
    runner = _make_runner(tmp_path)
    result = runner.load_latest_review()

    assert result == ""


def test_load_latest_review_returns_empty_when_dir_missing(tmp_path: Path) -> None:
    """load_latest_review deve ritornare stringa vuota se la cartella non esiste."""
    runner = _make_runner(tmp_path)
    # reports_dir non esiste ancora
    result = runner.load_latest_review()

    assert result == ""


# ---------- _latest_report_time ----------


def test_latest_report_time_parses_filename(tmp_path: Path) -> None:
    """_latest_report_time deve parsare correttamente il nome file."""
    reports_dir = tmp_path / "news_reports"
    _write_report(reports_dir, "2026-06-15_13-30.md")

    runner = _make_runner(tmp_path)
    result = runner._latest_report_time()

    expected = datetime(2026, 6, 15, 13, 30, tzinfo=timezone.utc)
    assert result == expected


def test_latest_report_time_returns_none_when_no_files(tmp_path: Path) -> None:
    """_latest_report_time deve ritornare None se non ci sono file."""
    runner = _make_runner(tmp_path)
    assert runner._latest_report_time() is None


def test_latest_report_time_returns_none_on_unparsable_filename(tmp_path: Path) -> None:
    """_latest_report_time deve ritornare None se il nome file non è parsabile."""
    reports_dir = tmp_path / "news_reports"
    _write_report(reports_dir, "invalid_filename.md")

    runner = _make_runner(tmp_path)
    assert runner._latest_report_time() is None
