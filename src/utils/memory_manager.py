from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.core.contracts import TradingCycleResult


class MemoryManager:
    """Persiste e recupera le decisioni dei cicli operativi su file JSONL."""

    def __init__(self, memory_dir: str | Path = "data/memory") -> None:
        self._memory_dir = Path(memory_dir)
        self._memory_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_cycle(
        self,
        symbol: str,
        result: TradingCycleResult,
        current_price: float | None,
    ) -> None:
        """Salva il riassunto di un ciclo completato nel file JSONL del simbolo."""
        record = {
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "action": result.trade_proposal.action.value,
            "order_type": result.trade_proposal.order_type.value,
            "confidence": result.trade_proposal.confidence,
            "reason": result.trade_proposal.reason,
            "quantity": result.trade_proposal.details.quantity,
            "price": current_price,
            "execution_status": result.execution_report.execution_status.value,
            "risk_decision": result.risk_assessment.risk_decision.value,
            "market_bias": result.market_analysis.market_bias.value,
        }
        path = self._symbol_path(symbol)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    def get_memory(self, symbol: str) -> list[dict]:
        """Ritorna le ultime 10 decisioni per il simbolo indicato."""
        return self._read_last_n(symbol, n=10)

    def get_performance_summary(self, symbol: str) -> str:
        """Genera un riassunto testuale delle ultime 10 SELL eseguite.

        Confronta ogni SELL con il BUY precedente per stabilire profitto o perdita.
        Ritorna stringa vuota se non ci sono abbastanza dati.
        """
        all_records = self._read_all(symbol)
        executed_sells = [
            r
            for r in all_records
            if r.get("action") == "SELL"
            and r.get("execution_status") == "EXECUTED"
            and r.get("price") is not None
        ]

        if not executed_sells:
            return ""

        last_sells = executed_sells[-10:]
        profits = 0
        losses = 0
        pct_changes: list[float] = []

        for sell in last_sells:
            sell_price: float = sell["price"]
            sell_idx = all_records.index(sell)

            # Trova il BUY EXECUTED più recente prima di questo SELL
            buy_price: float | None = None
            for record in reversed(all_records[:sell_idx]):
                if (
                    record.get("action") == "BUY"
                    and record.get("execution_status") == "EXECUTED"
                    and record.get("price") is not None
                ):
                    buy_price = record["price"]
                    break

            if buy_price is None or buy_price == 0:
                continue

            pct = (sell_price - buy_price) / buy_price * 100
            pct_changes.append(pct)
            if pct >= 0:
                profits += 1
            else:
                losses += 1

        if not pct_changes:
            return ""

        avg_pct = sum(pct_changes) / len(pct_changes)
        sign = "+" if avg_pct >= 0 else ""
        return (
            f"Ultimi {len(last_sells)} SELL eseguiti: {profits} in profitto, "
            f"{losses} in perdita. Performance media: {sign}{avg_pct:.1f}%."
        )

    def get_recent_performance(self, symbol: str) -> list[dict]:
        """Ritorna le ultime 10 decisioni come lista semplificata."""
        records = self._read_last_n(symbol, n=10)
        return [
            {
                "action": r.get("action"),
                "price": r.get("price"),
                "execution_status": r.get("execution_status"),
            }
            for r in records
        ]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _symbol_path(self, symbol: str) -> Path:
        return self._memory_dir / f"{symbol}.jsonl"

    def _read_all(self, symbol: str) -> list[dict]:
        path = self._symbol_path(symbol)
        if not path.exists():
            return []
        records: list[dict] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return records

    def _read_last_n(self, symbol: str, n: int) -> list[dict]:
        """Legge le ultime n righe dal file JSONL del simbolo."""
        path = self._symbol_path(symbol)
        if not path.exists():
            return []
        lines: list[str] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    lines.append(line)
        records: list[dict] = []
        for line in lines[-n:]:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records
