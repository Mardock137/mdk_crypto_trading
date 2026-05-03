from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from src.core.contracts import (
    InvestmentMandate,
    PerformanceReview,
    PerformanceStats,
)
from src.utils.memory_manager import MemoryManager


def build_performance_stats(
    symbol: str,
    memory_manager: MemoryManager,
    events: Iterable[dict[str, Any]],
    days: int = 7,
    strong_signal_threshold: float = 0.7,
    today: date | None = None,
) -> PerformanceStats:
    """Sintetizza i cicli degli ultimi ``days`` giorni in un ``PerformanceStats``.

    Calcolo deterministico (zero LLM): ogni campo e una semplice aggregazione
    sugli eventi passati in input. Gli eventi sono quelli letti da
    ``src/utils/event_log_reader.py``.

    ``today`` permette di forzare la data di riferimento nei test.
    ``strong_signal_threshold`` e la soglia di ``signal_strength`` oltre la
    quale un segnale e considerato "forte" e il mancato trade va segnalato.
    """
    reference = today or date.today()
    period_end = reference.isoformat()
    period_start = (reference - timedelta(days=days - 1)).isoformat()

    event_list = [e for e in events if isinstance(e, dict)]
    total_cycles = len(event_list)

    buy_executed = 0
    sell_executed = 0
    hold_count = 0
    sell_failed = 0
    strong_bullish_ignored = 0
    strong_bearish_ignored = 0

    last_executed_at: datetime | None = None

    for event in event_list:
        proposal = event.get("trade_proposal") or {}
        analysis = event.get("market_analysis") or {}
        report = event.get("execution_report") or {}

        action = proposal.get("action")
        execution_status = report.get("execution_status")

        if action == "HOLD":
            hold_count += 1
        if action == "BUY" and execution_status == "EXECUTED":
            buy_executed += 1
        if action in ("SELL", "SELL_OCO") and execution_status == "EXECUTED":
            sell_executed += 1
        if action in ("SELL", "SELL_OCO") and execution_status == "FAILED":
            sell_failed += 1

        if action == "HOLD":
            bias = analysis.get("market_bias")
            try:
                strength = float(analysis.get("signal_strength") or 0.0)
            except (TypeError, ValueError):
                strength = 0.0
            if strength >= strong_signal_threshold:
                if bias == "BULLISH":
                    strong_bullish_ignored += 1
                elif bias == "BEARISH":
                    strong_bearish_ignored += 1

        if execution_status == "EXECUTED":
            ts = _parse_timestamp(event.get("timestamp"))
            if ts and (last_executed_at is None or ts > last_executed_at):
                last_executed_at = ts

    hold_ratio = hold_count / total_cycles if total_cycles > 0 else 0.0

    if last_executed_at is None:
        days_without_executed_trade = days
    else:
        delta = reference - last_executed_at.date()
        days_without_executed_trade = max(0, delta.days)

    fifo_trades = memory_manager.compute_fifo_trades(symbol)
    if fifo_trades:
        last_trades = fifo_trades[-10:]
        realized_pnl_usdc = sum(t["realized_pnl"] for t in last_trades)
        avg_pnl_pct = sum(t["pnl_pct"] for t in last_trades) / len(last_trades)
    else:
        realized_pnl_usdc = 0.0
        avg_pnl_pct = 0.0

    return PerformanceStats(
        period_start=period_start,
        period_end=period_end,
        total_cycles=total_cycles,
        buy_executed=buy_executed,
        sell_executed=sell_executed,
        hold_count=hold_count,
        sell_failed=sell_failed,
        hold_ratio=round(hold_ratio, 4),
        strong_bullish_ignored=strong_bullish_ignored,
        strong_bearish_ignored=strong_bearish_ignored,
        realized_pnl_usdc=round(realized_pnl_usdc, 2),
        avg_pnl_pct=round(avg_pnl_pct, 2),
        days_without_executed_trade=days_without_executed_trade,
    )


def write_performance_report(
    symbol: str,
    mandate: InvestmentMandate,
    stats: PerformanceStats,
    review: PerformanceReview,
    days_analyzed: int,
    reports_dir: str | Path = "data/performance_reports",
    today: date | None = None,
) -> Path:
    """Serializza il report in markdown e lo salva in ``reports_dir/YYYY-MM-DD.md``.

    Ritorna il path del file scritto.
    """
    reference = today or date.today()
    target_dir = Path(reports_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    file_path = target_dir / f"{reference.isoformat()}.md"
    file_path.write_text(
        _format_markdown_report(symbol, mandate, stats, review, days_analyzed, reference),
        encoding="utf-8",
    )
    return file_path


def _format_markdown_report(
    symbol: str,
    mandate: InvestmentMandate,
    stats: PerformanceStats,
    review: PerformanceReview,
    days_analyzed: int,
    reference: date,
) -> str:
    hold_pct = stats.hold_ratio * 100
    pnl_sign = "+" if stats.realized_pnl_usdc >= 0 else ""
    avg_pct_sign = "+" if stats.avg_pnl_pct >= 0 else ""

    suggestions_block = "\n".join(
        f"- {s}" for s in review.suggestions
    ) or "- (nessun suggerimento)"

    return (
        f"# Performance Report — {reference.isoformat()}\n"
        "\n"
        f"**Simbolo**: {symbol}\n"
        f"**Periodo analizzato**: ultimi {days_analyzed} giorni "
        f"({stats.period_start} → {stats.period_end})\n"
        f"**Aderenza al mandato**: {review.mandate_adherence.value}\n"
        "\n"
        "## Sintesi\n"
        "\n"
        f"{review.summary}\n"
        "\n"
        "## Mandato operativo\n"
        "\n"
        f"- Drawdown massimo: {mandate.max_drawdown_pct:.1f}%\n"
        f"- Orizzonte: {mandate.horizon}\n"
        f"- Posizione massima: {mandate.max_position_pct:.1f}%\n"
        "\n"
        "## Statistiche\n"
        "\n"
        f"- Cicli totali: {stats.total_cycles}\n"
        f"- HOLD: {stats.hold_count} ({hold_pct:.1f}%)\n"
        f"- BUY eseguiti: {stats.buy_executed}\n"
        f"- SELL eseguiti: {stats.sell_executed}\n"
        f"- SELL falliti: {stats.sell_failed}\n"
        f"- Segnali BULLISH forti ignorati: {stats.strong_bullish_ignored}\n"
        f"- Segnali BEARISH forti ignorati: {stats.strong_bearish_ignored}\n"
        f"- Giorni senza trade eseguito: {stats.days_without_executed_trade}\n"
        f"- P&L realizzato: {pnl_sign}{stats.realized_pnl_usdc:.2f} USDC\n"
        f"- P&L medio: {avg_pct_sign}{stats.avg_pnl_pct:.2f}%\n"
        "\n"
        "## Suggerimenti\n"
        "\n"
        f"{suggestions_block}\n"
    )


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse ISO timestamp (con fallback per 'Z' alla fine) oppure None."""
    if not isinstance(value, str) or not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


__all__ = [
    "build_performance_stats",
    "write_performance_report",
]
