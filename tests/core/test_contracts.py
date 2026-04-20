from src.core.contracts import (
    ExecutionReport,
    ExecutionStatus,
    InvestmentMandate,
    MarketAnalysis,
    MarketBias,
    OrderType,
    RiskAssessment,
    RiskDecision,
    SuggestedAction,
    TradeAction,
    TradeProposal,
    TradeProposalDetails,
)


def test_trade_proposal_details_estimated_notional_uses_limit_price() -> None:
    details = TradeProposalDetails(quantity=0.5, price=100.0)

    assert details.estimated_notional() == 50.0


def test_trade_proposal_details_estimated_notional_can_use_reference_price() -> None:
    details = TradeProposalDetails(quantity=0.5)

    assert details.estimated_notional(reference_price=120.0) == 60.0


def test_trade_proposal_hold_property() -> None:
    proposal = TradeProposal(
        action=TradeAction.HOLD,
        order_type=OrderType.NONE,
        confidence=0.7,
        reason="No trade",
    )

    assert proposal.is_hold is True


def test_risk_assessment_approved_property() -> None:
    assessment = RiskAssessment(
        risk_decision=RiskDecision.APPROVE,
        confidence=0.9,
        reason="Valid proposal",
    )

    assert assessment.is_approved is True


def test_execution_report_was_executed_property() -> None:
    report = ExecutionReport(
        execution_status=ExecutionStatus.EXECUTED,
        executed_action=TradeAction.BUY,
        order_type=OrderType.MARKET,
        reason="Done",
    )

    assert report.was_executed is True


def test_investment_mandate_stores_all_fields() -> None:
    mandate = InvestmentMandate(
        objective="Rendimento su capitale",
        min_monthly_return_pct=2.0,
        max_drawdown_pct=15.0,
        horizon="Intraday to swing",
        max_position_pct=100.0,
        min_trades_per_week=3,
    )

    assert mandate.objective == "Rendimento su capitale"
    assert mandate.min_monthly_return_pct == 2.0
    assert mandate.max_drawdown_pct == 15.0
    assert mandate.horizon == "Intraday to swing"
    assert mandate.max_position_pct == 100.0
    assert mandate.min_trades_per_week == 3


def test_market_analysis_keeps_structured_signal_data() -> None:
    analysis = MarketAnalysis(
        market_bias=MarketBias.BULLISH,
        signal_strength=0.8,
        confidence=0.75,
        summary="Momentum is improving.",
        key_factors=["RSI rising"],
        risk_notes=["Resistance nearby"],
        suggested_action=SuggestedAction.LONG_BIAS,
    )

    assert analysis.market_bias is MarketBias.BULLISH
    assert analysis.suggested_action is SuggestedAction.LONG_BIAS

