from __future__ import annotations

from src.core import notifications
from src.core.contracts import (
    ExecutionReport,
    ExecutionStatus,
    MarketAnalysis,
    MarketBias,
    OrderType,
    RiskAssessment,
    RiskDecision,
    TradeAction,
    TradeProposal,
    TradeProposalDetails,
    TradingCycleResult,
)


def _market_analysis() -> MarketAnalysis:
    return MarketAnalysis(
        market_bias=MarketBias.NEUTRAL,
        signal_strength=0.0,
        confidence=0.5,
        summary="test",
    )


def _risk_assessment() -> RiskAssessment:
    return RiskAssessment(
        risk_decision=RiskDecision.APPROVE,
        confidence=0.9,
        reason="ok",
    )


def _result(
    execution_report: ExecutionReport, proposal: TradeProposal,
) -> TradingCycleResult:
    return TradingCycleResult(
        market_analysis=_market_analysis(),
        trade_proposal=proposal,
        risk_assessment=_risk_assessment(),
        execution_report=execution_report,
    )


def test_build_startup_message_contains_key_fields() -> None:
    msg = notifications.build_startup_message(
        symbol="BTCUSDC", mode="DEMO", interval_seconds=60,
    )

    assert "STARTED" in msg
    assert "BTCUSDC" in msg
    assert "DEMO" in msg
    assert "60s" in msg


def test_build_stop_message_contains_symbol() -> None:
    msg = notifications.build_stop_message(symbol="BTCUSDC")

    assert "STOPPED" in msg
    assert "BTCUSDC" in msg


def test_build_error_message_contains_correlation_id_and_type() -> None:
    msg = notifications.build_error_message(
        symbol="BTCUSDC",
        correlation_id="a1b2c3d4",
        exc_class="RuntimeError",
    )

    assert "ERROR" in msg
    assert "BTCUSDC" in msg
    assert "a1b2c3d4" in msg
    assert "RuntimeError" in msg
    assert "Error ID:" in msg


def test_build_order_notification_market_computes_avg_price() -> None:
    report = ExecutionReport(
        execution_status=ExecutionStatus.EXECUTED,
        executed_action=TradeAction.BUY,
        order_type=OrderType.MARKET,
        reason="ok",
        execution_details={
            "cummulativeQuoteQty": "27.43",
            "executedQty": "0.0004",
        },
    )
    proposal = TradeProposal(
        action=TradeAction.BUY,
        order_type=OrderType.MARKET,
        confidence=0.63,
        reason="test",
        details=TradeProposalDetails(quantity=0.0004),
    )

    msg = notifications.build_order_notification(
        symbol="BTCUSDC", mode="DEMO", result=_result(report, proposal),
    )

    assert "EXECUTED" in msg
    assert "BUY" in msg
    assert "MARKET" in msg
    assert "Price: 68575.00" in msg
    assert "Value: 27.43 USDC" in msg
    assert "DM Confidence: 0.63" in msg
    assert "BTCUSDC" in msg


def test_build_order_notification_market_handles_invalid_details() -> None:
    """Se i campi Binance sono assenti o non parsabili, il messaggio non crasha."""
    report = ExecutionReport(
        execution_status=ExecutionStatus.EXECUTED,
        executed_action=TradeAction.BUY,
        order_type=OrderType.MARKET,
        reason="ok",
        execution_details={},
    )
    proposal = TradeProposal(
        action=TradeAction.BUY,
        order_type=OrderType.MARKET,
        confidence=0.5,
        reason="test",
        details=TradeProposalDetails(quantity=0.001),
    )

    msg = notifications.build_order_notification(
        symbol="BTCUSDC", mode="DEMO", result=_result(report, proposal),
    )

    assert "EXECUTED" in msg
    assert "Price:" not in msg
    assert "Value:" not in msg


def test_build_order_notification_limit_uses_proposal_price() -> None:
    report = ExecutionReport(
        execution_status=ExecutionStatus.EXECUTED,
        executed_action=TradeAction.BUY,
        order_type=OrderType.LIMIT,
        reason="ok",
        execution_details={},
    )
    proposal = TradeProposal(
        action=TradeAction.BUY,
        order_type=OrderType.LIMIT,
        confidence=0.7,
        reason="test",
        details=TradeProposalDetails(quantity=0.001, price=50000.0),
    )

    msg = notifications.build_order_notification(
        symbol="BTCUSDC", mode="REAL", result=_result(report, proposal),
    )

    assert "Price: 50000.00" in msg
    assert "Est. Value: 50.00 USDC" in msg
    assert "REAL" in msg
