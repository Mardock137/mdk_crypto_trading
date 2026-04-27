from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_recent_events(
    symbol: str,
    days: int = 7,
    events_dir: str | Path = _PROJECT_ROOT / "logs/events",
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Legge gli eventi operativi dell'exchange negli ultimi ``days`` giorni.

    Ogni file JSONL in ``events_dir`` contiene una riga per ciclo. Vengono
    lette le righe relative al simbolo indicato, scartando righe malformate
    o riferite ad altri simboli.

    ``today`` permette di forzare la data di riferimento nei test.
    """
    base = Path(events_dir)
    if not base.exists():
        return []

    reference = today or date.today()
    events: list[dict[str, Any]] = []

    for offset in range(days):
        day = reference - timedelta(days=offset)
        file_path = base / f"{day.isoformat()}.jsonl"
        if not file_path.exists():
            continue

        with file_path.open("r", encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                if record.get("symbol") != symbol:
                    continue
                events.append(record)

    events.sort(key=lambda r: str(r.get("timestamp", "")))
    return events
