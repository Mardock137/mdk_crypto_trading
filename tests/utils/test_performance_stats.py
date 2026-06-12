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
    mm.get_price_equity_series.return_value = []
    mm.compute_open_position.return_value = None
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
    mm.get_price_equity_series.return_value = []
    stats = build_performance_stats(
        "BTCUSDC", mm, [], days=7, today=date(2026, 4, 20),
    )

    assert stats.realized_pnl_usdc == pytest.approx(2.0)
    assert stats.avg_pnl_pct == pytest.approx(0.25)
    assert stats.sells_in_profit == 1
    assert stats.sells_in_loss == 1


def test_build_stats_sells_in_profit_and_loss_zero_without_trades() -> None:
    stats = build_performance_stats(
        "BTCUSDC", _mock_mm_without_trades(), [], days=7,
        today=date(2026, 4, 20),
    )

    assert stats.sells_in_profit == 0
    assert stats.sells_in_loss == 0


def test_build_stats_sells_in_profit_counts_breakeven_as_profit() -> None:
    """pnl_pct == 0 viene contato come profitto (>= 0), simmetrico a get_performance_summary."""
    mm = MagicMock()
    mm.compute_fifo_trades.return_value = [
        {"realized_pnl": 5.0, "pnl_pct": 1.0},
        {"realized_pnl": 0.0, "pnl_pct": 0.0},
        {"realized_pnl": -2.0, "pnl_pct": -1.0},
    ]
    mm.get_price_equity_series.return_value = []
    stats = build_performance_stats(
        "BTCUSDC", mm, [], days=7, today=date(2026, 4, 20),
    )

    assert stats.sells_in_profit == 2
    assert stats.sells_in_loss == 1


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
    assert "SELL in profitto" in content
    assert "SELL in perdita" in content


# ---------- KPI cumulativi (tutti i trade) ----------


def test_build_stats_realized_pnl_total_usdc_uses_all_trades() -> None:
    """realized_pnl_total_usdc deve sommare tutti i trade FIFO, non solo gli ultimi 10."""
    mm = MagicMock()
    mm.compute_fifo_trades.return_value = [
        {"realized_pnl": 10.0, "pnl_pct": 2.0},
    ] * 15  # 15 trade
    mm.get_price_equity_series.return_value = []
    stats = build_performance_stats(
        "BTCUSDC", mm, [], days=7, today=date(2026, 4, 20),
    )

    assert stats.realized_pnl_total_usdc == pytest.approx(150.0)


def test_build_stats_win_rate_pct_all_wins() -> None:
    """win_rate_pct deve essere 100% se tutti i trade sono vincenti."""
    mm = MagicMock()
    mm.compute_fifo_trades.return_value = [
        {"realized_pnl": 5.0, "pnl_pct": 1.0},
        {"realized_pnl": 3.0, "pnl_pct": 0.5},
    ]
    mm.get_price_equity_series.return_value = []
    stats = build_performance_stats(
        "BTCUSDC", mm, [], days=7, today=date(2026, 4, 20),
    )

    assert stats.win_rate_pct == pytest.approx(100.0)
    assert stats.avg_win_pct == pytest.approx(0.75)
    assert stats.avg_loss_pct == pytest.approx(0.0)


def test_build_stats_win_rate_and_avg_win_loss_mixed() -> None:
    """win_rate_pct, avg_win_pct e avg_loss_pct devono essere calcolati correttamente su un mix."""
    mm = MagicMock()
    mm.compute_fifo_trades.return_value = [
        {"realized_pnl": 4.0, "pnl_pct": 2.0},
        {"realized_pnl": 6.0, "pnl_pct": 3.0},
        {"realized_pnl": -2.0, "pnl_pct": -1.0},
    ]
    mm.get_price_equity_series.return_value = []
    stats = build_performance_stats(
        "BTCUSDC", mm, [], days=7, today=date(2026, 4, 20),
    )

    assert stats.win_rate_pct == pytest.approx(100 * 2 / 3, rel=1e-4)
    assert stats.avg_win_pct == pytest.approx(2.5)
    assert stats.avg_loss_pct == pytest.approx(1.0)


def test_build_stats_cumulative_kpis_zero_without_trades() -> None:
    """Senza trade i KPI cumulativi devono essere zero."""
    stats = build_performance_stats(
        "BTCUSDC", _mock_mm_without_trades(), [], days=7,
        today=date(2026, 4, 20),
    )

    assert stats.realized_pnl_total_usdc == 0.0
    assert stats.win_rate_pct == 0.0
    assert stats.avg_win_pct == 0.0
    assert stats.avg_loss_pct == 0.0


# ---------- KPI equity-based ----------


def _mock_mm_with_equity(equity_series: list[dict]) -> MagicMock:
    mm = MagicMock()
    mm.compute_fifo_trades.return_value = []
    mm.get_price_equity_series.return_value = equity_series
    mm.compute_open_position.return_value = None
    return mm


def test_build_stats_buy_and_hold_and_strategy_return() -> None:
    """buy_and_hold_return_pct e strategy_return_pct devono essere calcolati dalla serie."""
    series = [
        {"timestamp": "2026-04-14T10:00:00", "price": 60000.0, "equity_usdc": 1000.0},
        {"timestamp": "2026-04-20T10:00:00", "price": 63000.0, "equity_usdc": 1100.0},
    ]
    stats = build_performance_stats(
        "BTCUSDC", _mock_mm_with_equity(series), [], days=7,
        today=date(2026, 4, 20),
    )

    assert stats.buy_and_hold_return_pct == pytest.approx(5.0, rel=1e-4)
    assert stats.strategy_return_pct == pytest.approx(10.0, rel=1e-4)


def test_build_stats_max_drawdown_from_equity() -> None:
    """max_drawdown_pct deve rilevare la discesa massima dal picco."""
    series = [
        {"timestamp": "2026-04-14T10:00:00", "price": 60000.0, "equity_usdc": 1000.0},
        {"timestamp": "2026-04-15T10:00:00", "price": 62000.0, "equity_usdc": 1200.0},
        {"timestamp": "2026-04-16T10:00:00", "price": 58000.0, "equity_usdc": 900.0},
        {"timestamp": "2026-04-20T10:00:00", "price": 61000.0, "equity_usdc": 1050.0},
    ]
    stats = build_performance_stats(
        "BTCUSDC", _mock_mm_with_equity(series), [], days=7,
        today=date(2026, 4, 20),
    )

    # Picco 1200, minimo 900 → drawdown = (1200-900)/1200*100 = 25%
    assert stats.max_drawdown_pct == pytest.approx(25.0, rel=1e-4)


def test_build_stats_equity_kpis_none_without_series() -> None:
    """Senza serie equity i KPI equity-based devono essere None."""
    stats = build_performance_stats(
        "BTCUSDC", _mock_mm_without_trades(), [], days=7,
        today=date(2026, 4, 20),
    )

    assert stats.buy_and_hold_return_pct is None
    assert stats.strategy_return_pct is None
    assert stats.max_drawdown_pct is None


def test_build_stats_equity_kpis_none_with_single_point() -> None:
    """Con un solo punto nella serie equity i KPI equity-based devono essere None."""
    mm = _mock_mm_with_equity([
        {"timestamp": "2026-04-20T10:00:00", "price": 60000.0, "equity_usdc": 1000.0},
    ])
    stats = build_performance_stats(
        "BTCUSDC", mm, [], days=7, today=date(2026, 4, 20),
    )

    assert stats.buy_and_hold_return_pct is None
    assert stats.strategy_return_pct is None
    assert stats.max_drawdown_pct is None


# ---------- Report markdown: sezione KPI ----------


def test_write_performance_report_includes_kpi_section(tmp_path: Path) -> None:
    """Il report markdown deve includere la sezione ## KPI con tutti i nuovi campi."""
    mandate = InvestmentMandate(
        max_drawdown_pct=15.0,
        horizon="Intraday to swing",
        max_position_pct=70.0,
    )
    mm = _mock_mm_with_equity([
        {"timestamp": "2026-04-14T10:00:00", "price": 60000.0, "equity_usdc": 1000.0},
        {"timestamp": "2026-04-20T10:00:00", "price": 63000.0, "equity_usdc": 1100.0},
    ])
    stats = build_performance_stats(
        "BTCUSDC", mm, [], days=7, today=date(2026, 4, 20),
    )
    review = PerformanceReview(
        summary="OK",
        mandate_adherence=MandateAdherence.ALIGNED,
        suggestions=["Nessuna azione"],
    )

    path = write_performance_report(
        "BTCUSDC", mandate, stats, review, days_analyzed=7,
        reports_dir=tmp_path, today=date(2026, 4, 20),
    )
    content = path.read_text(encoding="utf-8")

    assert "## KPI" in content
    assert "Win rate" in content
    assert "Vincita media" in content
    assert "Perdita media" in content
    assert "Rendimento strategia" in content
    assert "buy-and-hold" in content
    assert "Max drawdown" in content


def test_write_performance_report_kpi_shows_nd_when_equity_missing(tmp_path: Path) -> None:
    """Il report deve mostrare 'n/d' per i KPI equity-based quando la serie è assente."""
    mandate = InvestmentMandate(
        max_drawdown_pct=15.0,
        horizon="Intraday to swing",
        max_position_pct=70.0,
    )
    stats = build_performance_stats(
        "BTCUSDC", _mock_mm_without_trades(), [], days=7,
        today=date(2026, 4, 20),
    )
    review = PerformanceReview(
        summary="OK",
        mandate_adherence=MandateAdherence.ALIGNED,
        suggestions=["s1"],
    )

    path = write_performance_report(
        "BTCUSDC", mandate, stats, review, days_analyzed=7,
        reports_dir=tmp_path, today=date(2026, 4, 20),
    )
    content = path.read_text(encoding="utf-8")

    assert "n/d" in content


# ---------- has_open_position ----------


def test_build_stats_has_open_position_true_when_position_exists() -> None:
    """has_open_position deve essere True se compute_open_position ritorna un dict."""
    mm = MagicMock()
    mm.compute_fifo_trades.return_value = []
    mm.get_price_equity_series.return_value = []
    mm.compute_open_position.return_value = {"open_qty": 0.001, "avg_entry_price": 60000.0}
    stats = build_performance_stats(
        "BTCUSDC", mm, [], days=7, today=date(2026, 4, 20),
    )

    assert stats.has_open_position is True


def test_build_stats_has_open_position_false_when_flat() -> None:
    """has_open_position deve essere False se compute_open_position ritorna None."""
    mm = MagicMock()
    mm.compute_fifo_trades.return_value = []
    mm.get_price_equity_series.return_value = []
    mm.compute_open_position.return_value = None
    stats = build_performance_stats(
        "BTCUSDC", mm, [], days=7, today=date(2026, 4, 20),
    )

    assert stats.has_open_position is False
