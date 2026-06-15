"""Test per src/utils/news_report.py."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.core.contracts import NewsDigest, NewsSentiment
from src.utils.news_report import write_news_report, _format_news_markdown_report


# ---------- helpers ----------


def _make_digest(
    sentiment: NewsSentiment = NewsSentiment.BULLISH,
    summary: str = "Sentiment rialzista.",
    key_events: list[str] | None = None,
    risk_flags: list[str] | None = None,
) -> NewsDigest:
    return NewsDigest(
        overall_sentiment=sentiment,
        summary=summary,
        key_events=key_events if key_events is not None else ["ETF inflows record"],
        risk_flags=risk_flags if risk_flags is not None else [],
    )


_FIXED_NOW = datetime(2026, 6, 15, 13, 30, 0, tzinfo=timezone.utc)


# ---------- write_news_report ----------


def test_write_creates_file_in_reports_dir(tmp_path: Path) -> None:
    """write_news_report deve creare il file nella cartella indicata."""
    digest = _make_digest()
    path = write_news_report(
        symbol="BTCUSDC",
        digest=digest,
        hours_analyzed=12,
        reports_dir=tmp_path,
        now=_FIXED_NOW,
    )

    assert path.exists()
    assert path.parent == tmp_path


def test_write_creates_directory_if_missing(tmp_path: Path) -> None:
    """write_news_report deve creare la cartella se non esiste."""
    reports_dir = tmp_path / "sub" / "news_reports"
    assert not reports_dir.exists()

    write_news_report(
        symbol="BTCUSDC",
        digest=_make_digest(),
        hours_analyzed=12,
        reports_dir=reports_dir,
        now=_FIXED_NOW,
    )

    assert reports_dir.exists()


def test_write_filename_format(tmp_path: Path) -> None:
    """Il nome file deve essere YYYY-MM-DD_HH-MM.md (Windows-safe, ordinabile)."""
    path = write_news_report(
        symbol="BTCUSDC",
        digest=_make_digest(),
        hours_analyzed=12,
        reports_dir=tmp_path,
        now=_FIXED_NOW,
    )

    assert path.name == "2026-06-15_13-30.md"


def test_write_returns_path_of_written_file(tmp_path: Path) -> None:
    """write_news_report deve ritornare il Path del file scritto."""
    path = write_news_report(
        symbol="BTCUSDC",
        digest=_make_digest(),
        hours_analyzed=12,
        reports_dir=tmp_path,
        now=_FIXED_NOW,
    )

    assert isinstance(path, Path)
    assert path.suffix == ".md"


# ---------- _format_news_markdown_report ----------


def test_format_contains_sentiment(tmp_path: Path) -> None:
    """Il markdown deve contenere il sentiment."""
    digest = _make_digest(sentiment=NewsSentiment.BEARISH)
    content = _format_news_markdown_report("BTCUSDC", digest, 12, _FIXED_NOW)

    assert "BEARISH" in content


def test_format_contains_summary(tmp_path: Path) -> None:
    """Il markdown deve contenere la sintesi."""
    digest = _make_digest(summary="Pressione ribassista forte.")
    content = _format_news_markdown_report("BTCUSDC", digest, 12, _FIXED_NOW)

    assert "Pressione ribassista forte." in content


def test_format_contains_key_events() -> None:
    """Il markdown deve contenere gli eventi chiave."""
    digest = _make_digest(key_events=["Hack exchange da 100M$"])
    content = _format_news_markdown_report("BTCUSDC", digest, 12, _FIXED_NOW)

    assert "Hack exchange da 100M$" in content


def test_format_contains_risk_flags() -> None:
    """Il markdown deve contenere i risk flag."""
    digest = _make_digest(risk_flags=["Possibile contagio sentiment"])
    content = _format_news_markdown_report("BTCUSDC", digest, 12, _FIXED_NOW)

    assert "Possibile contagio sentiment" in content


def test_format_no_key_events_shows_placeholder() -> None:
    """Se non ci sono eventi chiave, deve apparire un placeholder."""
    digest = _make_digest(key_events=[])
    content = _format_news_markdown_report("BTCUSDC", digest, 12, _FIXED_NOW)

    assert "nessun evento chiave" in content


def test_format_no_risk_flags_shows_placeholder() -> None:
    """Se non ci sono risk flag, deve apparire un placeholder."""
    digest = _make_digest(risk_flags=[])
    content = _format_news_markdown_report("BTCUSDC", digest, 12, _FIXED_NOW)

    assert "nessun risk flag" in content


def test_format_contains_symbol_and_hours() -> None:
    """Il markdown deve contenere il simbolo e la finestra analizzata."""
    digest = _make_digest()
    content = _format_news_markdown_report("BTCUSDC", digest, 24, _FIXED_NOW)

    assert "BTCUSDC" in content
    assert "24" in content


def test_format_neutral_full_report(tmp_path: Path) -> None:
    """Un digest NEUTRAL con liste vuote deve produrre un report valido."""
    digest = NewsDigest(
        overall_sentiment=NewsSentiment.NEUTRAL,
        summary="Nessuna notizia rilevante.",
        key_events=[],
        risk_flags=[],
    )
    path = write_news_report(
        symbol="BTCUSDC",
        digest=digest,
        hours_analyzed=12,
        reports_dir=tmp_path,
        now=_FIXED_NOW,
    )
    content = path.read_text(encoding="utf-8")

    assert "NEUTRAL" in content
    assert "Nessuna notizia rilevante." in content
