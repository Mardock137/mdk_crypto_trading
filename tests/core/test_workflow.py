from src.core.contracts import (
    DecisionMakerInput,
    ExecutionInput,
    ExecutionReport,
    ExecutionStatus,
    InvestmentMandate,
    MarketAnalysis,
    MarketBias,
    MarketDataSnapshot,
    MarketAnalystInput,
    OperationConstraints,
    OrderType,
    PortfolioState,
    RiskAssessment,
    RiskDecision,
    RiskManagerInput,
    SuggestedAction,
    TradeAction,
    TradeProposal,
    TradeProposalDetails,
    TradingCycleInput,
)
from src.core.workflow import TradingWorkflow


class DummyMarketAnalyst:
    def __init__(self, call_order: list[str]) -> None:
        self.call_order = call_order

    def run(self, agent_input: MarketAnalystInput) -> MarketAnalysis:
        self.call_order.append("market_analyst")
        assert agent_input.symbol == "BTCUSDC"
        return MarketAnalysis(
            market_bias=MarketBias.BULLISH,
            signal_strength=0.8,
            confidence=0.75,
            summary="Bullish bias.",
            suggested_action=SuggestedAction.LONG_BIAS,
        )


class DummyDecisionMaker:
    def __init__(self, call_order: list[str]) -> None:
        self.call_order = call_order

    def run(self, agent_input: DecisionMakerInput) -> TradeProposal:
        self.call_order.append("decision_maker")
        assert agent_input.market_analysis.market_bias is MarketBias.BULLISH
        assert agent_input.mandate.min_trades_per_week == 3
        return TradeProposal(
            action=TradeAction.BUY,
            order_type=OrderType.MARKET,
            confidence=0.8,
            reason="Buy signal confirmed.",
            details=TradeProposalDetails(quantity=0.01),
        )


class DummyRiskManager:
    def __init__(self, call_order: list[str]) -> None:
        self.call_order = call_order

    def run(self, agent_input: RiskManagerInput) -> RiskAssessment:
        self.call_order.append("risk_manager")
        assert agent_input.proposal.action is TradeAction.BUY
        return RiskAssessment(
            risk_decision=RiskDecision.APPROVE,
            confidence=0.9,
            reason="Proposal is valid.",
        )


class DummyExecutionTrader:
    def __init__(self, call_order: list[str]) -> None:
        self.call_order = call_order

    def run(self, agent_input: ExecutionInput) -> ExecutionReport:
        self.call_order.append("execution_trader")
        assert agent_input.risk_assessment.risk_decision is RiskDecision.APPROVE
        return ExecutionReport(
            execution_status=ExecutionStatus.EXECUTED,
            executed_action=TradeAction.BUY,
            order_type=OrderType.MARKET,
            reason="Order executed.",
            execution_details={"quantity": 0.01},
        )


def test_workflow_runs_agents_in_expected_order() -> None:
    call_order: list[str] = []
    workflow = TradingWorkflow(
        market_analyst=DummyMarketAnalyst(call_order),
        decision_maker=DummyDecisionMaker(call_order),
        risk_manager=DummyRiskManager(call_order),
        execution_trader=DummyExecutionTrader(call_order),
    )

    cycle_input = TradingCycleInput(
        symbol="BTCUSDC",
        market_data=MarketDataSnapshot(symbol="BTCUSDC", price=100000.0),
        portfolio=PortfolioState(
            usdc_balance=1000.0,
            usdc_balance_total=1000.0,
            usdc_value=0.0,
            portfolio_qty_free=0.0,
            portfolio_qty_total=0.0,
        ),
        constraints=OperationConstraints(
            cycle_interval_seconds=7200,
            min_order_usdc=10.0,
        ),
        mandate=InvestmentMandate(
            objective="Rendimento sul capitale",
            min_monthly_return_pct=2.0,
            max_drawdown_pct=15.0,
            horizon="Intraday to swing",
            max_position_pct=100.0,
            min_trades_per_week=3,
        ),
    )

    result = workflow.run_cycle(cycle_input)

    assert call_order == [
        "market_analyst",
        "decision_maker",
        "risk_manager",
        "execution_trader",
    ]
    assert result.trade_proposal.action is TradeAction.BUY
    assert result.risk_assessment.is_approved is True
    assert result.execution_report.was_executed is True

