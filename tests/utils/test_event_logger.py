from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from src.core.contracts import (
    CycleContextSnapshot,
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
)
from src.utils.event_logger import EventLogger


def _sample_market_analysis() -> MarketAnalysis:
    return MarketAnalysis(
        market_bias=MarketBias.BULLISH,
        signal_strength=0.78,
        confidence=0.74,
        summary="Mercato rialzista",
        suggested_action=SuggestedAction.LONG_BIAS,
    )


def _sample_trade_proposal() -> TradeProposal:
    return TradeProposal(
        action=TradeAction.BUY,
        order_type=OrderType.MARKET,
        confidence=0.82,
        reason="Segnale forte",
    )


def _sample_risk_assessment() -> RiskAssessment:
    return RiskAssessment(
        risk_decision=RiskDecision.APPROVE,
        confidence=0.91,
        reason="Rischio accettabile",
    )


def _sample_execution_report() -> ExecutionReport:
    return ExecutionReport(
        execution_status=ExecutionStatus.EXECUTED,
        executed_action=TradeAction.BUY,
        order_type=OrderType.MARKET,
        reason="Ordine eseguito",
    )


def test_log_cycle_creates_jsonl_file(tmp_path: Path) -> None:
    """log_cycle deve creare il file .jsonl nella cartella corretta."""
    logger = EventLogger(events_dir=tmp_path)

    logger.log_cycle(
        symbol="BTCUSDC",
        trading_mode="DEMO",
        market_analysis=_sample_market_analysis(),
        trade_proposal=_sample_trade_proposal(),
        risk_assessment=_sample_risk_assessment(),
        execution_report=_sample_execution_report(),
    )

    expected_file = tmp_path / f"{date.today().isoformat()}.jsonl"
    assert expected_file.exists()


def test_log_cycle_writes_expected_fields(tmp_path: Path) -> None:
    """Il JSON scritto da log_cycle deve contenere tutti i campi attesi."""
    logger = EventLogger(events_dir=tmp_path)

    logger.log_cycle(
        symbol="BTCUSDC",
        trading_mode="DEMO",
        market_analysis=_sample_market_analysis(),
        trade_proposal=_sample_trade_proposal(),
        risk_assessment=_sample_risk_assessment(),
        execution_report=_sample_execution_report(),
    )

    jsonl_file = tmp_path / f"{date.today().isoformat()}.jsonl"
    record = json.loads(jsonl_file.read_text(encoding="utf-8").strip())

    assert record["symbol"] == "BTCUSDC"
    assert record["trading_mode"] == "DEMO"
    assert record["error"] is None

    assert record["market_analysis"]["market_bias"] == "BULLISH"
    assert record["trade_proposal"]["action"] == "BUY"
    assert record["risk_assessment"]["risk_decision"] == "APPROVE"
    assert record["execution_report"]["execution_status"] == "EXECUTED"


def test_log_error_writes_error_field(tmp_path: Path) -> None:
    """log_error deve scrivere il campo error con gli altri campi a null."""
    logger = EventLogger(events_dir=tmp_path)

    logger.log_error(
        symbol="ETHUSDC",
        trading_mode="DEMO",
        error="Connessione fallita",
    )

    jsonl_file = tmp_path / f"{date.today().isoformat()}.jsonl"
    record = json.loads(jsonl_file.read_text(encoding="utf-8").strip())

    assert record["symbol"] == "ETHUSDC"
    assert record["error"] == "Connessione fallita"
    assert record["market_analysis"] is None
    assert record["trade_proposal"] is None
    assert record["risk_assessment"] is None
    assert record["execution_report"] is None


def test_log_error_serializes_partial_results(tmp_path: Path) -> None:
    """log_error serializza correttamente i parziali quando vengono passati."""
    logger = EventLogger(events_dir=tmp_path)

    logger.log_error(
        symbol="BTCUSDC",
        trading_mode="DEMO",
        error="Decision Maker boom",
        correlation_id="abc12345",
        market_analysis=_sample_market_analysis(),
        trade_proposal=_sample_trade_proposal(),
        risk_assessment=None,
    )

    jsonl_file = tmp_path / f"{date.today().isoformat()}.jsonl"
    record = json.loads(jsonl_file.read_text(encoding="utf-8").strip())

    assert record["error"] == "Decision Maker boom"
    assert record["correlation_id"] == "abc12345"
    assert record["market_analysis"]["market_bias"] == "BULLISH"
    assert record["trade_proposal"]["action"] == "BUY"
    assert record["risk_assessment"] is None
    assert record["execution_report"] is None


def test_log_skipped_cycle_writes_expected_fields(tmp_path: Path) -> None:
    """log_skipped_cycle deve scrivere un record con cycle_type=skipped."""
    logger = EventLogger(events_dir=tmp_path)
    snapshot = CycleContextSnapshot(
        price=100.0,
        rsi=52.0,
        macd=1.0,
        macd_signal=0.5,
        previous_action=TradeAction.HOLD,
        open_order_ids={"abc", "xyz"},
    )

    logger.log_skipped_cycle(
        symbol="BTCUSDC",
        trading_mode="DEMO",
        reason="context unchanged within thresholds",
        snapshot=snapshot,
    )

    jsonl_file = tmp_path / f"{date.today().isoformat()}.jsonl"
    record = json.loads(jsonl_file.read_text(encoding="utf-8").strip())

    assert record["cycle_type"] == "skipped"
    assert record["symbol"] == "BTCUSDC"
    assert record["trading_mode"] == "DEMO"
    assert record["reason"] == "context unchanged within thresholds"
    assert record["snapshot"]["price"] == 100.0
    assert record["snapshot"]["previous_action"] == "HOLD"
    assert sorted(record["snapshot"]["open_order_ids"]) == ["abc", "xyz"]
