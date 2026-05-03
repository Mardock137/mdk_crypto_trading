from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.core.contracts import (
    InvestmentMandate,
    MandateAdherence,
    PerformanceReview,
)
from src.utils.performance_stats import (
    build_performance_stats,
    write_performance_report,
)


def _event(
    *,
    action: str = "HOLD",
    market_bias: str = "NEUTRAL",
    signal_strength: float = 0.5,
    execution_status: str = "NOT_EXECUTED",
    timestamp: str = "2026-04-20T10:00:00+00:00",
) -> dict:
    return {
        "timestamp": timestamp,
        "symbol": "BTCUSDC",
        "trade_proposal": {"action": action},
        "market_analysis": {
            "market_bias": market_bias,
            "signal_strength": signal_strength,
        },
        "execution_report": {"execution_status": execution_status},
    }


def _mock_mm_without_trades() -> MagicMock:
    mm = MagicMock()
    mm.compute_fifo_trades.return_value = []
    return mm


# ---------- Counters ----------


def test_build_stats_counters_basic() -> None:
    events = [
        _event(action="HOLD"),
        _event(action="HOLD"),
        _event(action="BUY", execution_status="EXECUTED"),
        _event(action="SELL", execution_status="EXECUTED"),
        _event(action="SELL", execution_status="FAILED"),
    ]
    stats = build_performance_stats(
        "BTCUSDC", _mock_mm_without_trades(), events, days=7,
        today=date(2026, 4, 20),
    )

    assert stats.total_cycles == 5
    assert stats.hold_count == 2
    assert stats.buy_executed == 1
    assert stats.sell_executed == 1
    assert stats.sell_failed == 1
    assert stats.hold_ratio == pytest.approx(0.4)


def test_build_stats_sell_oco_counted_as_sell_executed() -> None:
    events = [
        _event(action="SELL_OCO", execution_status="EXECUTED"),
        _event(action="SELL_OCO", execution_status="FAILED"),
    ]
    stats = build_performance_stats(
        "BTCUSDC", _mock_mm_without_trades(), events, days=7,
        today=date(2026, 4, 20),
    )

    assert stats.sell_executed == 1
    assert stats.sell_failed == 1


def test_build_stats_strong_signal_ignored() -> None:
    events = [
        _event(action="HOLD", market_bias="BULLISH", signal_strength=0.8),
        _event(action="HOLD", market_bias="BULLISH", signal_strength=0.4),
        _event(action="HOLD", market_bias="BEARISH", signal_strength=0.9),
        _event(action="BUY", market_bias="BULLISH", signal_strength=0.8, execution_status="EXECUTED"),
    ]
    stats = build_performance_stats(
        "BTCUSDC", _mock_mm_without_trades(), events, days=7,
        today=date(2026, 4, 20),
    )

    assert stats.strong_bullish_ignored == 1
    assert stats.strong_bearish_ignored == 1


def test_build_stats_handles_empty_events() -> None:
    stats = build_performance_stats(
        "BTCUSDC", _mock_mm_without_trades(), [], days=7,
        today=date(2026, 4, 20),
    )

    assert stats.total_cycles == 0
    assert stats.hold_ratio == 0.0
    assert stats.days_without_executed_trade == 7


def test_build_stats_days_without_executed_trade() -> None:
    events = [
        _event(
            action="BUY", execution_status="EXECUTED",
            timestamp="2026-04-18T10:00:00+00:00",
        ),
        _event(action="HOLD", timestamp="2026-04-19T10:00:00+00:00"),
        _event(action="HOLD", timestamp="2026-04-20T10:00:00+00:00"),
    ]
    stats = build_performance_stats(
        "BTCUSDC", _mock_mm_without_trades(), events, days=7,
        today=date(2026, 4, 20),
    )

    assert stats.days_without_executed_trade == 2


def test_build_stats_uses_fifo_trades_for_pnl() -> None:
    mm = MagicMock()
    mm.compute_fifo_trades.return_value = [
        {"realized_pnl": 5.0, "pnl_pct": 1.0},
        {"realized_pnl": -3.0, "pnl_pct": -0.5},
    ]
    stats = build_performance_stats(
        "BTCUSDC", mm, [], days=7, today=date(2026, 4, 20),
    )

    assert stats.realized_pnl_usdc == pytest.approx(2.0)
    assert stats.avg_pnl_pct == pytest.approx(0.25)


def test_build_stats_period_dates() -> None:
    stats = build_performance_stats(
        "BTCUSDC", _mock_mm_without_trades(), [], days=7,
        today=date(2026, 4, 20),
    )

    assert stats.period_end == "2026-04-20"
    assert stats.period_start == "2026-04-14"


# ---------- write_performance_report ----------


def test_write_performance_report_creates_file(tmp_path: Path) -> None:
    mandate = InvestmentMandate(
        max_drawdown_pct=15.0,
        horizon="Intraday to swing",
        max_position_pct=70.0,
    )
    stats = build_performance_stats(
        "BTCUSDC", _mock_mm_without_trades(),
        [_event(action="HOLD")], days=7,
        today=date(2026, 4, 20),
    )
    review = PerformanceReview(
        summary="Sistema in drift: troppi HOLD.",
        mandate_adherence=MandateAdherence.DRIFTING,
        suggestions=["Agire sui segnali forti", "Verificare soglia"],
    )

    path = write_performance_report(
        "BTCUSDC", mandate, stats, review, days_analyzed=7,
        reports_dir=tmp_path, today=date(2026, 4, 20),
    )

    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "Performance Report — 2026-04-20" in content
    assert "DRIFTING" in content
    assert "Agire sui segnali forti" in content
