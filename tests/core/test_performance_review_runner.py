from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.contracts import (
    InvestmentMandate,
    MandateAdherence,
    PerformanceReview,
    PerformanceStats,
)
from src.core.performance_review_runner import PerformanceReviewRunner


_MANDATE = InvestmentMandate(
    max_drawdown_pct=15.0,
    horizon="Intraday to swing",
    max_position_pct=70.0,
)


def _make_runner(reports_dir: Path, reviewer: MagicMock | None = None) -> tuple[
    PerformanceReviewRunner, MagicMock,
]:
    reviewer_mock = reviewer or MagicMock()
    runner = PerformanceReviewRunner(
        symbol="BTCUSDC",
        mandate=_MANDATE,
        memory_manager=MagicMock(),
        performance_reviewer=reviewer_mock,
        reports_dir=reports_dir,
        logger=logging.getLogger("mdk_crypto_trading.test_performance_review_runner"),
    )
    return runner, reviewer_mock


def _stats() -> PerformanceStats:
    return PerformanceStats(
        period_start="2026-04-14",
        period_end="2026-04-20",
        total_cycles=10,
        buy_executed=1,
        sell_executed=0,
        hold_count=9,
        sell_failed=0,
        hold_ratio=0.9,
        strong_bullish_ignored=0,
        strong_bearish_ignored=0,
        realized_pnl_usdc=0.0,
        avg_pnl_pct=0.0,
        days_without_executed_trade=3,
    )


def test_maybe_run_today_skips_when_today_report_exists(tmp_path: Path) -> None:
    today_file = tmp_path / f"{date.today().isoformat()}.md"
    today_file.write_text("existing", encoding="utf-8")
    runner, reviewer = _make_runner(tmp_path)

    runner.maybe_run_today()

    reviewer.run.assert_not_called()


@patch("src.core.performance_review_runner.build_performance_stats")
@patch("src.core.performance_review_runner.load_recent_events", return_value=[])
def test_maybe_run_today_writes_report_when_missing(
    mock_events: MagicMock, mock_build: MagicMock, tmp_path: Path,
) -> None:
    mock_build.return_value = _stats()
    reviewer = MagicMock()
    reviewer.run.return_value = PerformanceReview(
        summary="Test review",
        mandate_adherence=MandateAdherence.ALIGNED,
        suggestions=["s1"],
    )
    runner, _ = _make_runner(tmp_path, reviewer=reviewer)

    runner.maybe_run_today()

    reviewer.run.assert_called_once()
    today_file = tmp_path / f"{date.today().isoformat()}.md"
    assert today_file.exists()


@patch(
    "src.core.performance_review_runner.load_recent_events",
    side_effect=RuntimeError("boom"),
)
def test_maybe_run_today_does_not_raise_on_failure(
    mock_events: MagicMock, tmp_path: Path,
) -> None:
    runner, reviewer = _make_runner(tmp_path)

    runner.maybe_run_today()

    reviewer.run.assert_not_called()


def test_load_latest_review_returns_empty_when_dir_missing(tmp_path: Path) -> None:
    runner, _ = _make_runner(tmp_path / "missing")

    assert runner.load_latest_review() == ""


def test_load_latest_review_returns_empty_when_no_files(tmp_path: Path) -> None:
    runner, _ = _make_runner(tmp_path)

    assert runner.load_latest_review() == ""


def test_load_latest_review_returns_most_recent_file_content(tmp_path: Path) -> None:
    (tmp_path / "2026-04-18.md").write_text("older", encoding="utf-8")
    (tmp_path / "2026-04-19.md").write_text("latest content", encoding="utf-8")
    runner, _ = _make_runner(tmp_path)

    assert runner.load_latest_review() == "latest content"
