from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from src.utils.event_log_reader import load_recent_events


def _write_event(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def test_load_recent_events_returns_events_for_symbol(tmp_path: Path) -> None:
    today = date(2026, 4, 20)
    _write_event(tmp_path / "2026-04-20.jsonl", {"symbol": "BTCUSDC", "timestamp": "2026-04-20T10:00:00+00:00"})
    _write_event(tmp_path / "2026-04-19.jsonl", {"symbol": "BTCUSDC", "timestamp": "2026-04-19T10:00:00+00:00"})
    _write_event(tmp_path / "2026-04-18.jsonl", {"symbol": "ETHUSDC", "timestamp": "2026-04-18T10:00:00+00:00"})

    events = load_recent_events("BTCUSDC", days=7, events_dir=tmp_path, today=today)

    assert len(events) == 2
    assert all(e["symbol"] == "BTCUSDC" for e in events)
    assert events[0]["timestamp"] < events[1]["timestamp"]


def test_load_recent_events_returns_empty_if_dir_missing(tmp_path: Path) -> None:
    assert load_recent_events("BTCUSDC", events_dir=tmp_path / "missing") == []


def test_load_recent_events_skips_malformed_lines(tmp_path: Path) -> None:
    today = date(2026, 4, 20)
    file_path = tmp_path / "2026-04-20.jsonl"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        '{"symbol": "BTCUSDC", "timestamp": "2026-04-20T10:00:00+00:00"}\n'
        'not-a-json-line\n'
        '{"symbol": "BTCUSDC", "timestamp": "2026-04-20T11:00:00+00:00"}\n'
        '\n',
        encoding="utf-8",
    )

    events = load_recent_events("BTCUSDC", days=1, events_dir=tmp_path, today=today)

    assert len(events) == 2


def test_load_recent_events_respects_days_window(tmp_path: Path) -> None:
    today = date(2026, 4, 20)
    _write_event(tmp_path / "2026-04-20.jsonl", {"symbol": "BTCUSDC", "timestamp": "2026-04-20T10:00:00+00:00"})
    _write_event(tmp_path / "2026-04-10.jsonl", {"symbol": "BTCUSDC", "timestamp": "2026-04-10T10:00:00+00:00"})

    events = load_recent_events("BTCUSDC", days=3, events_dir=tmp_path, today=today)

    assert len(events) == 1
    assert events[0]["timestamp"].startswith("2026-04-20")
