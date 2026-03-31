from __future__ import annotations

from pathlib import Path

import pytest

from src.core.contracts import (
    ExecutionReport,
    ExecutionStatus,
    MarketAnalysis,
    MarketBias,
    OrderType,
    RiskAssessment,
    RiskDecision,
    SuggestedAction,
    TradeAction,
    TradeProposal,
    TradeProposalDetails,
    TradingCycleResult,
)
from src.utils.memory_manager import MemoryManager


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_result(
    action: TradeAction = TradeAction.BUY,
    execution_status: ExecutionStatus = ExecutionStatus.EXECUTED,
    confidence: float = 0.75,
    quantity: float | None = 0.001,
) -> TradingCycleResult:
    return TradingCycleResult(
        market_analysis=MarketAnalysis(
            market_bias=MarketBias.BULLISH,
            signal_strength=0.8,
            confidence=0.7,
            summary="Test analysis",
            suggested_action=SuggestedAction.LONG_BIAS,
        ),
        trade_proposal=TradeProposal(
            action=action,
            order_type=OrderType.MARKET,
            confidence=confidence,
            reason="Test reason",
            details=TradeProposalDetails(quantity=quantity),
        ),
        risk_assessment=RiskAssessment(
            risk_decision=RiskDecision.APPROVE,
            confidence=0.9,
            reason="Test risk",
        ),
        execution_report=ExecutionReport(
            execution_status=execution_status,
            executed_action=action,
            order_type=OrderType.MARKET,
            reason="Test execution",
        ),
    )


# ------------------------------------------------------------------
# save_cycle
# ------------------------------------------------------------------


def test_save_cycle_creates_jsonl_file(tmp_path: Path) -> None:
    """save_cycle deve creare il file JSONL per il simbolo."""
    mm = MemoryManager(memory_dir=tmp_path)
    mm.save_cycle(symbol="BTCUSDC", result=_make_result(), current_price=67000.0)

    assert (tmp_path / "BTCUSDC.jsonl").exists()


def test_save_cycle_writes_expected_fields(tmp_path: Path) -> None:
    """save_cycle deve scrivere tutti i campi attesi nel record JSONL."""
    import json

    mm = MemoryManager(memory_dir=tmp_path)
    mm.save_cycle(symbol="BTCUSDC", result=_make_result(), current_price=67000.0)

    lines = (tmp_path / "BTCUSDC.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    record = json.loads(lines[0])
    assert record["action"] == "BUY"
    assert record["order_type"] == "MARKET"
    assert record["execution_status"] == "EXECUTED"
    assert record["risk_decision"] == "APPROVE"
    assert record["market_bias"] == "BULLISH"
    assert record["price"] == pytest.approx(67000.0)
    assert "timestamp" in record


# ------------------------------------------------------------------
# get_memory
# ------------------------------------------------------------------


def test_get_memory_returns_last_10(tmp_path: Path) -> None:
    """get_memory deve ritornare le ultime 10 decisioni anche se ce ne sono 15."""
    mm = MemoryManager(memory_dir=tmp_path)

    for i in range(15):
        mm.save_cycle(
            symbol="BTCUSDC",
            result=_make_result(confidence=float(i) / 100),
            current_price=float(60000 + i),
        )

    records = mm.get_memory("BTCUSDC")
    assert len(records) == 10
    # Verifica che siano le ultime 10 (prezzi da 60005 a 60014)
    assert records[0]["price"] == pytest.approx(60005.0)
    assert records[-1]["price"] == pytest.approx(60014.0)


def test_get_memory_returns_empty_for_missing_symbol(tmp_path: Path) -> None:
    """get_memory deve ritornare lista vuota se il simbolo non ha file."""
    mm = MemoryManager(memory_dir=tmp_path)
    assert mm.get_memory("ETHUSDC") == []


# ------------------------------------------------------------------
# get_recent_performance
# ------------------------------------------------------------------


def test_get_recent_performance_returns_simplified_list(tmp_path: Path) -> None:
    """get_recent_performance deve ritornare lista con action, price, execution_status."""
    mm = MemoryManager(memory_dir=tmp_path)
    mm.save_cycle(symbol="BTCUSDC", result=_make_result(action=TradeAction.BUY), current_price=65000.0)
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.HOLD, execution_status=ExecutionStatus.NOT_EXECUTED),
        current_price=None,
    )

    perf = mm.get_recent_performance("BTCUSDC")
    assert len(perf) == 2
    assert set(perf[0].keys()) == {"action", "price", "execution_status"}
    assert perf[0]["action"] == "BUY"
    assert perf[0]["price"] == pytest.approx(65000.0)
    assert perf[1]["action"] == "HOLD"
    assert perf[1]["execution_status"] == "NOT_EXECUTED"


# ------------------------------------------------------------------
# get_performance_summary
# ------------------------------------------------------------------


def test_get_performance_summary_with_data(tmp_path: Path) -> None:
    """get_performance_summary deve ritornare una stringa non vuota con dati sufficienti."""
    mm = MemoryManager(memory_dir=tmp_path)

    # BUY a 60000, poi SELL a 62000 → profitto
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, execution_status=ExecutionStatus.EXECUTED),
        current_price=60000.0,
    )
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.SELL, execution_status=ExecutionStatus.EXECUTED),
        current_price=62000.0,
    )

    summary = mm.get_performance_summary("BTCUSDC")
    assert isinstance(summary, str)
    assert len(summary) > 0
    assert "SELL" in summary


def test_get_performance_summary_without_sell_returns_empty(tmp_path: Path) -> None:
    """get_performance_summary deve ritornare stringa vuota senza SELL eseguiti."""
    mm = MemoryManager(memory_dir=tmp_path)
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, execution_status=ExecutionStatus.EXECUTED),
        current_price=60000.0,
    )

    summary = mm.get_performance_summary("BTCUSDC")
    assert summary == ""
