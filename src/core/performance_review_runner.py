from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from src.agents.performance_reviewer import PerformanceReviewerAgent
from src.core.contracts import InvestmentMandate, PerformanceReviewerInput
from src.utils.event_log_reader import load_recent_events
from src.utils.memory_manager import MemoryManager
from src.utils.performance_stats import build_performance_stats, write_performance_report


class PerformanceReviewRunner:
    """Orchestra il giudizio giornaliero del Performance Reviewer."""

    def __init__(
        self,
        symbol: str,
        mandate: InvestmentMandate,
        memory_manager: MemoryManager,
        performance_reviewer: PerformanceReviewerAgent,
        reports_dir: Path,
        logger: logging.Logger,
        days: int = 7,
    ) -> None:
        self._symbol = symbol
        self._mandate = mandate
        self._memory_manager = memory_manager
        self._performance_reviewer = performance_reviewer
        self._reports_dir = reports_dir
        self._logger = logger
        self._days = days

    def maybe_run_today(self) -> None:
        """Genera il report giornaliero se non esiste già per oggi.

        Errori del Reviewer non bloccano il ciclo: vengono loggati come warning.
        """
        today = date.today()
        today_report = self._reports_dir / f"{today.isoformat()}.md"
        if today_report.exists():
            return

        try:
            events = load_recent_events(self._symbol, days=self._days)
            stats = build_performance_stats(
                symbol=self._symbol,
                memory_manager=self._memory_manager,
                events=events,
                days=self._days,
            )
            review = self._performance_reviewer.run(
                PerformanceReviewerInput(
                    symbol=self._symbol,
                    mandate=self._mandate,
                    stats=stats,
                    days_analyzed=self._days,
                )
            )
            write_performance_report(
                symbol=self._symbol,
                mandate=self._mandate,
                stats=stats,
                review=review,
                days_analyzed=self._days,
                reports_dir=self._reports_dir,
            )
            self._logger.info(
                "Performance Reviewer → %s (%d suggerimenti)",
                review.mandate_adherence.value,
                len(review.suggestions),
            )
        except Exception as exc:
            self._logger.warning(
                "Performance Reviewer fallito (ciclo continua): %s", exc,
            )

    def load_latest_review(self) -> str:
        """Ritorna il contenuto del report più recente, o stringa vuota."""
        if not self._reports_dir.exists():
            return ""
        files = sorted(self._reports_dir.glob("*.md"))
        if not files:
            return ""
        try:
            return files[-1].read_text(encoding="utf-8")
        except OSError:
            return ""
