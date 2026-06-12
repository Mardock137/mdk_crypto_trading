from __future__ import annotations

import json
import re
from collections import deque
from datetime import date, datetime, timezone
from pathlib import Path

from src.core.contracts import TradingCycleResult

_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,20}$")


class MemoryManager:
    """Persiste e recupera le decisioni dei cicli operativi su file JSONL.

    Cache per-ciclo
    ---------------
    Dentro un ciclo il file JSONL è statico: l'unico writer è ``save_cycle``,
    chiamato **dopo** tutte le letture. Le due cache interne (``_records_cache``
    per i record grezzi, ``_fifo_cache`` per i risultati della camminata FIFO)
    vengono popolate al primo accesso e invalidate da ``save_cycle`` alla
    scrittura. I chiamanti di ``_read_all`` e ``_walk_fifo`` NON devono mutare
    le strutture restituite: la cache condivide gli oggetti tra chiamate dello
    stesso ciclo.
    """

    def __init__(self, memory_dir: str | Path = "data/memory") -> None:
        self._memory_dir = Path(memory_dir)
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        self._records_cache: dict[str, list[dict]] = {}
        self._fifo_cache: dict[str, tuple[list[dict], deque[list[float]]]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_cycle(
        self,
        symbol: str,
        result: TradingCycleResult,
        current_price: float | None,
        equity_usdc: float | None = None,
    ) -> None:
        """Salva il riassunto di un ciclo completato nel file JSONL del simbolo."""
        record: dict = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
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
        if equity_usdc is not None:
            record["equity_usdc"] = equity_usdc
        path = self._symbol_path(symbol)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        self._records_cache.pop(symbol, None)
        self._fifo_cache.pop(symbol, None)

    def get_memory(self, symbol: str) -> list[dict]:
        """Ritorna le ultime 10 decisioni per il simbolo indicato."""
        return self._read_last_n(symbol, n=10)

    def get_performance_summary(self, symbol: str) -> str:
        """Genera un riassunto testuale delle ultime 10 vendite calcolate con metodo FIFO.

        Ritorna stringa vuota se non ci sono vendite realizzate.
        """
        fifo_trades = self.compute_fifo_trades(symbol)
        if not fifo_trades:
            return ""

        last_trades = fifo_trades[-10:]
        profits = sum(1 for t in last_trades if t["pnl_pct"] >= 0)
        losses = len(last_trades) - profits
        avg_pct = sum(t["pnl_pct"] for t in last_trades) / len(last_trades)
        total_pnl = sum(t["realized_pnl"] for t in last_trades)

        avg_sign = "+" if avg_pct >= 0 else ""
        total_sign = "+" if total_pnl >= 0 else ""
        return (
            f"Ultimi {len(last_trades)} SELL (FIFO): {profits} in profitto, "
            f"{losses} in perdita. "
            f"P&L medio: {avg_sign}{avg_pct:.1f}%. "
            f"P&L totale: {total_sign}{total_pnl:.2f} USDC."
        )

    def get_recent_performance(self, symbol: str) -> list[dict]:
        """Ritorna le ultime 10 decisioni come lista semplificata.

        Per le SELL eseguite include anche i dati FIFO (realized_pnl, pnl_pct).
        """
        fifo_by_idx = self._build_fifo_index(symbol)
        all_records = self._read_all(symbol)
        total = len(all_records)
        last_10_start = max(0, total - 10)

        result: list[dict] = []
        for i, record in enumerate(all_records[last_10_start:], start=last_10_start):
            entry: dict = {
                "action": record.get("action"),
                "price": record.get("price"),
                "quantity": record.get("quantity"),
                "execution_status": record.get("execution_status"),
            }
            if i in fifo_by_idx:
                entry["realized_pnl"] = fifo_by_idx[i]["realized_pnl"]
                entry["pnl_pct"] = fifo_by_idx[i]["pnl_pct"]
            result.append(entry)
        return result

    def compact(self, symbol: str, keep_last_n: int) -> int:
        """Compatta il file JSONL del simbolo rimuovendo i record piu vecchi.

        Mantiene gli ultimi ``keep_last_n`` record reali e preserva i lotti BUY
        aperti presenti nella finestra pre-cutoff come record sintetici, in modo
        che il FIFO riparta da uno stato coerente senza dover rileggere tutto lo
        storico originale.

        La scrittura e' atomica: prima scrive su ``<symbol>.jsonl.tmp``, poi
        rinomina via ``replace()`` che e' atomico su tutti i sistemi operativi.
        Al termine invalida ``_records_cache`` e ``_fifo_cache`` per il simbolo.

        Ritorna il numero di record originali del pre-cutoff rimossi (>= 0).
        Se ``keep_last_n >= total``, non fa nulla e ritorna 0.
        """
        records = self._read_all(symbol)
        total = len(records)
        cutoff = total - keep_last_n
        if cutoff <= 0:
            return 0

        pre_cutoff = records[:cutoff]
        post_cutoff = records[cutoff:]

        _, lot_queue = self._fifo_walk(pre_cutoff)

        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        synthetic_records = [
            {
                "timestamp": now_ts,
                "action": "BUY",
                "order_type": "LIMIT",
                "confidence": None,
                "reason": "[compacted]",
                "quantity": qty,
                "price": price,
                "execution_status": "EXECUTED",
                "risk_decision": None,
                "market_bias": None,
                "_compacted": True,
            }
            for qty, price in lot_queue
            if qty > 0
        ]

        new_records = synthetic_records + post_cutoff
        path = self._symbol_path(symbol)
        tmp_path = path.parent / (path.name + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as fh:
            for rec in new_records:
                fh.write(json.dumps(rec) + "\n")
        tmp_path.replace(path)

        self._records_cache.pop(symbol, None)
        self._fifo_cache.pop(symbol, None)
        return cutoff

    def compact_if_needed(self, symbol: str, threshold: int, keep_last_n: int) -> int:
        """Compatta solo se il numero di record ha raggiunto la soglia.

        Ritorna il numero di record rimossi, oppure 0 se la soglia non e' stata
        raggiunta e nessuna azione e' stata eseguita.
        """
        records = self._read_all(symbol)
        if len(records) < threshold:
            return 0
        return self.compact(symbol, keep_last_n)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _symbol_path(self, symbol: str) -> Path:
        if not _SYMBOL_RE.fullmatch(symbol):
            raise ValueError(f"Symbol non valido: {symbol!r}")
        return self._memory_dir / f"{symbol}.jsonl"

    def _read_all(self, symbol: str) -> list[dict]:
        if symbol in self._records_cache:
            return self._records_cache[symbol]
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
        self._records_cache[symbol] = records
        return records

    def _read_last_n(self, symbol: str, n: int) -> list[dict]:
        """Ritorna le ultime n righe passando dalla cache di _read_all."""
        return self._read_all(symbol)[-n:]

    @staticmethod
    def _fifo_walk(records: list[dict]) -> tuple[list[dict], deque[list[float]]]:
        """Logica FIFO pura su una lista di record, senza cache.

        Ogni BUY EXECUTED aggiunge un lotto (quantity, price) in coda.
        Ogni SELL EXECUTED consuma i lotti partendo dal piu vecchio.
        Vendite parziali attraverso piu lotti vengono aggregate con costo medio ponderato.
        Ignora record con quantity o price mancanti/invalidi.

        Ritorna una tupla (results, lot_queue):
        - results: lista di dict con le chiavi
            record_idx, sell_price, avg_cost_basis, qty_consumed, realized_pnl, pnl_pct
        - lot_queue: deque dei lotti BUY ancora aperti (non consumati da SELL),
          ognuno come [qty_residua, price]
        """
        lot_queue: deque[list[float]] = deque()
        results: list[dict] = []

        for i, record in enumerate(records):
            action = record.get("action")
            status = record.get("execution_status")
            quantity = record.get("quantity")
            price = record.get("price")

            if status != "EXECUTED":
                continue
            if quantity is None or price is None:
                continue
            try:
                qty = float(quantity)
                px = float(price)
            except (TypeError, ValueError):
                continue
            if qty <= 0 or px <= 0:
                continue

            if action == "BUY":
                lot_queue.append([qty, px])

            elif action == "SELL":
                remaining_sell = qty
                total_cost = 0.0
                total_qty_consumed = 0.0

                while remaining_sell > 0 and lot_queue:
                    lot_qty, lot_price = lot_queue[0]
                    consumed = min(lot_qty, remaining_sell)
                    total_cost += consumed * lot_price
                    total_qty_consumed += consumed
                    remaining_sell -= consumed
                    lot_queue[0][0] -= consumed
                    if lot_queue[0][0] <= 0:
                        lot_queue.popleft()

                if total_qty_consumed <= 0:
                    continue

                avg_cost = total_cost / total_qty_consumed
                realized_pnl = total_qty_consumed * (px - avg_cost)
                pnl_pct = (px - avg_cost) / avg_cost * 100

                results.append({
                    "record_idx": i,
                    "sell_price": px,
                    "avg_cost_basis": avg_cost,
                    "qty_consumed": total_qty_consumed,
                    "realized_pnl": realized_pnl,
                    "pnl_pct": pnl_pct,
                })

        return results, lot_queue

    def _walk_fifo(self, symbol: str) -> tuple[list[dict], deque[list[float]]]:
        """Wrapper con cache attorno a _fifo_walk: legge tutti i record e li processa."""
        if symbol in self._fifo_cache:
            return self._fifo_cache[symbol]
        records = self._read_all(symbol)
        result = self._fifo_walk(records)
        self._fifo_cache[symbol] = result
        return result

    def compute_fifo_trades(self, symbol: str) -> list[dict]:
        """Calcola le vendite realizzate usando il metodo FIFO.

        Ritorna lista di dict con: sell_price, avg_cost_basis, quantity,
        realized_pnl (USDC), pnl_pct (%).
        """
        results, _ = self._walk_fifo(symbol)
        return [
            {
                "sell_price": entry["sell_price"],
                "avg_cost_basis": round(entry["avg_cost_basis"], 8),
                "quantity": round(entry["qty_consumed"], 8),
                "realized_pnl": round(entry["realized_pnl"], 4),
                "pnl_pct": round(entry["pnl_pct"], 4),
            }
            for entry in results
        ]

    def _build_fifo_index(self, symbol: str) -> dict[int, dict]:
        """Mappa indice del record SELL -> dati FIFO, per arricchire get_recent_performance."""
        results, _ = self._walk_fifo(symbol)
        return {
            entry["record_idx"]: {
                "realized_pnl": round(entry["realized_pnl"], 4),
                "pnl_pct": round(entry["pnl_pct"], 4),
            }
            for entry in results
        }

    def compute_open_position(self, symbol: str) -> dict | None:
        """Calcola la posizione aperta (FIFO) per il simbolo.

        Aggrega i lotti BUY non ancora consumati dalle SELL e ritorna un dict con:
        - open_qty: quantita totale ancora aperta
        - avg_entry_price: prezzo medio ponderato di carico

        Ritorna None se non c'e nessuna posizione aperta.
        """
        _, lot_queue = self._walk_fifo(symbol)
        if not lot_queue:
            return None

        total_qty = 0.0
        total_cost = 0.0
        for qty, price in lot_queue:
            if qty <= 0:
                continue
            total_qty += qty
            total_cost += qty * price

        if total_qty <= 0:
            return None

        return {
            "open_qty": round(total_qty, 8),
            "avg_entry_price": round(total_cost / total_qty, 8),
        }

    def get_price_equity_series(
        self,
        symbol: str,
        since: date | None = None,
        until: date | None = None,
    ) -> list[dict]:
        """Ritorna la serie temporale di prezzo ed equity nella finestra indicata.

        Ogni entry contiene:
        - ``timestamp`` (str): timestamp del record.
        - ``price`` (float | None): prezzo del ciclo (None se assente/invalido).
        - ``equity_usdc`` (float | None): valore totale del portafoglio (None per
          i record precedenti alla v1.27.0, che non registravano questo campo).

        I limiti ``since`` / ``until`` sono inclusivi e confrontati sulla data
        (i primi 10 caratteri del timestamp). Passare ``None`` rimuove il filtro
        sul lato corrispondente.
        """
        records = self._read_all(symbol)
        result: list[dict] = []
        for record in records:
            ts_str = record.get("timestamp")
            if not isinstance(ts_str, str) or len(ts_str) < 10:
                continue
            try:
                rec_date = date.fromisoformat(ts_str[:10])
            except ValueError:
                continue
            if since is not None and rec_date < since:
                continue
            if until is not None and rec_date > until:
                continue

            raw_price = record.get("price")
            try:
                price_val: float | None = float(raw_price) if raw_price is not None else None
            except (TypeError, ValueError):
                price_val = None

            raw_equity = record.get("equity_usdc")
            try:
                equity_val: float | None = (
                    float(raw_equity) if raw_equity is not None else None
                )
            except (TypeError, ValueError):
                equity_val = None

            result.append({
                "timestamp": ts_str,
                "price": price_val,
                "equity_usdc": equity_val,
            })
        return result
