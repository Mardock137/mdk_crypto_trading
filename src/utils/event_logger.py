from __future__ import annotations

import dataclasses
import json
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from src.core.contracts import (
    CycleContextSnapshot,
    ExecutionReport,
    MarketAnalysis,
    RiskAssessment,
    TradeProposal,
)


class EventLogger:
    """Logger strutturato in JSON per registrare le decisioni di ogni ciclo operativo.

    Scrive un file .jsonl al giorno in ``events_dir`` (una riga JSON per ciclo).
    """

    def __init__(self, events_dir: str | Path = "logs/events") -> None:
        self._events_dir = Path(events_dir)
        self._events_dir.mkdir(parents=True, exist_ok=True)

    def log_cycle(
        self,
        symbol: str,
        trading_mode: str,
        market_analysis: MarketAnalysis,
        trade_proposal: TradeProposal,
        risk_assessment: RiskAssessment,
        execution_report: ExecutionReport,
    ) -> None:
        """Registra un ciclo operativo completato con successo."""
        record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "symbol": symbol,
            "trading_mode": trading_mode,
            "market_analysis": dataclasses.asdict(market_analysis),
            "trade_proposal": dataclasses.asdict(trade_proposal),
            "risk_assessment": dataclasses.asdict(risk_assessment),
            "execution_report": dataclasses.asdict(execution_report),
            "error": None,
        }
        self._append(record)

    def log_skipped_cycle(
        self,
        symbol: str,
        trading_mode: str,
        reason: str,
        snapshot: CycleContextSnapshot,
    ) -> None:
        """Registra un ciclo saltato dal pre-check deterministico.

        Scrive solo i campi essenziali (marker ``cycle_type=skipped``, motivo,
        snapshot di riferimento) senza i payload degli agenti.
        """
        record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "symbol": symbol,
            "trading_mode": trading_mode,
            "cycle_type": "skipped",
            "reason": reason,
            "snapshot": {
                "price": snapshot.price,
                "rsi": snapshot.rsi,
                "macd": snapshot.macd,
                "macd_signal": snapshot.macd_signal,
                "previous_action": snapshot.previous_action.value,
                "open_order_ids": sorted(snapshot.open_order_ids),
            },
            "error": None,
        }
        self._append(record)

    def log_error(
        self,
        symbol: str,
        trading_mode: str,
        error: str,
        correlation_id: str = "",
    ) -> None:
        """Registra un ciclo fallito con errore.

        ``correlation_id`` è un token corto (es. 8 hex) che collega questo
        record al messaggio Telegram di errore e al log locale, senza esporre
        il dettaglio dell'eccezione fuori dai log interni.
        """
        record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "symbol": symbol,
            "trading_mode": trading_mode,
            "market_analysis": None,
            "trade_proposal": None,
            "risk_assessment": None,
            "execution_report": None,
            "error": error,
            "correlation_id": correlation_id or None,
        }
        self._append(record)

    def _append(self, record: dict[str, Any]) -> None:
        """Aggiunge una riga JSON al file del giorno corrente."""
        file_path = self._events_dir / f"{date.today().isoformat()}.jsonl"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=_json_default, ensure_ascii=False) + "\n")


def _json_default(obj: object) -> Any:
    """Serializza Enum come valore stringa per la compatibilità JSON."""
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(f"Oggetto di tipo {type(obj).__name__} non serializzabile in JSON")
