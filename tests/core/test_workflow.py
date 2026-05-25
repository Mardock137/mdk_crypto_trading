from unittest.mock import MagicMock

import pytest

from src.agents.execution_trader import ExecutionTraderAgent
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
from src.core.exceptions import CycleExecutionError
from src.core.workflow import TradingWorkflow


def _make_cycle_input() -> TradingCycleInput:
    return TradingCycleInput(
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
            max_order_notional_usdc=100.0,
        ),
        mandate=InvestmentMandate(
            max_drawdown_pct=15.0,
            horizon="Intraday to swing",
            max_position_pct=70.0,
        ),
        latest_performance_review="fake review content",
    )


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
        assert agent_input.mandate.max_drawdown_pct == 15.0
        assert agent_input.latest_performance_review == "fake review content"
        assert agent_input.current_price == pytest.approx(100000.0)
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


class DummyBlockingRiskManager:
    def run(self, agent_input: RiskManagerInput) -> RiskAssessment:
        return RiskAssessment(
            risk_decision=RiskDecision.BLOCK,
            confidence=0.9,
            reason="Rischio troppo alto.",
        )


class DummyAdjustmentRiskManager:
    def run(self, agent_input: RiskManagerInput) -> RiskAssessment:
        return RiskAssessment(
            risk_decision=RiskDecision.REQUEST_ADJUSTMENT,
            confidence=0.7,
            reason="Ridurre la quantità.",
            required_changes=["Ridurre qty a 0.005"],
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
            max_order_notional_usdc=100.0,
        ),
        mandate=InvestmentMandate(
            max_drawdown_pct=15.0,
            horizon="Intraday to swing",
            max_position_pct=70.0,
        ),
        latest_performance_review="fake review content",
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


def test_workflow_does_not_execute_when_risk_blocks() -> None:
    exchange_client = MagicMock()
    workflow = TradingWorkflow(
        market_analyst=DummyMarketAnalyst([]),
        decision_maker=DummyDecisionMaker([]),
        risk_manager=DummyBlockingRiskManager(),
        execution_trader=ExecutionTraderAgent(
            exchange_client=exchange_client,
            kill_switch=False,
        ),
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
            max_order_notional_usdc=100.0,
        ),
        mandate=InvestmentMandate(
            max_drawdown_pct=15.0,
            horizon="Intraday to swing",
            max_position_pct=70.0,
        ),
        latest_performance_review="fake review content",
    )

    result = workflow.run_cycle(cycle_input)

    assert result.risk_assessment.is_approved is False
    assert result.execution_report.execution_status is ExecutionStatus.NOT_EXECUTED
    exchange_client.place_market_order.assert_not_called()
    exchange_client.place_limit_order.assert_not_called()
    exchange_client.cancel_order.assert_not_called()


def test_workflow_raises_cycle_execution_error_when_market_analyst_fails() -> None:
    market_analyst = MagicMock()
    market_analyst.run.side_effect = RuntimeError("MA boom")

    workflow = TradingWorkflow(
        market_analyst=market_analyst,
        decision_maker=MagicMock(),
        risk_manager=MagicMock(),
        execution_trader=MagicMock(),
    )

    with pytest.raises(CycleExecutionError) as exc_info:
        workflow.run_cycle(_make_cycle_input())

    assert isinstance(exc_info.value.original, RuntimeError)
    assert exc_info.value.market_analysis is None
    assert exc_info.value.trade_proposal is None
    assert exc_info.value.risk_assessment is None


def test_workflow_raises_cycle_execution_error_when_decision_maker_fails() -> None:
    decision_maker = MagicMock()
    decision_maker.run.side_effect = RuntimeError("DM boom")

    workflow = TradingWorkflow(
        market_analyst=DummyMarketAnalyst([]),
        decision_maker=decision_maker,
        risk_manager=MagicMock(),
        execution_trader=MagicMock(),
    )

    with pytest.raises(CycleExecutionError) as exc_info:
        workflow.run_cycle(_make_cycle_input())

    assert isinstance(exc_info.value.original, RuntimeError)
    assert exc_info.value.market_analysis is not None
    assert exc_info.value.market_analysis.market_bias is MarketBias.BULLISH
    assert exc_info.value.trade_proposal is None
    assert exc_info.value.risk_assessment is None


def test_workflow_raises_cycle_execution_error_when_risk_manager_fails() -> None:
    risk_manager = MagicMock()
    risk_manager.run.side_effect = RuntimeError("RM boom")

    workflow = TradingWorkflow(
        market_analyst=DummyMarketAnalyst([]),
        decision_maker=DummyDecisionMaker([]),
        risk_manager=risk_manager,
        execution_trader=MagicMock(),
    )

    with pytest.raises(CycleExecutionError) as exc_info:
        workflow.run_cycle(_make_cycle_input())

    assert isinstance(exc_info.value.original, RuntimeError)
    assert exc_info.value.market_analysis is not None
    assert exc_info.value.trade_proposal is not None
    assert exc_info.value.trade_proposal.action is TradeAction.BUY
    assert exc_info.value.risk_assessment is None


def test_workflow_raises_cycle_execution_error_when_execution_trader_fails() -> None:
    execution_trader = MagicMock()
    execution_trader.run.side_effect = RuntimeError("ET boom")

    workflow = TradingWorkflow(
        market_analyst=DummyMarketAnalyst([]),
        decision_maker=DummyDecisionMaker([]),
        risk_manager=DummyRiskManager([]),
        execution_trader=execution_trader,
    )

    with pytest.raises(CycleExecutionError) as exc_info:
        workflow.run_cycle(_make_cycle_input())

    assert isinstance(exc_info.value.original, RuntimeError)
    assert exc_info.value.market_analysis is not None
    assert exc_info.value.trade_proposal is not None
    assert exc_info.value.risk_assessment is not None
    assert exc_info.value.risk_assessment.risk_decision is RiskDecision.APPROVE


def test_workflow_does_not_execute_when_risk_requests_adjustment() -> None:
    exchange_client = MagicMock()
    workflow = TradingWorkflow(
        market_analyst=DummyMarketAnalyst([]),
        decision_maker=DummyDecisionMaker([]),
        risk_manager=DummyAdjustmentRiskManager(),
        execution_trader=ExecutionTraderAgent(
            exchange_client=exchange_client,
            kill_switch=False,
        ),
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
            max_order_notional_usdc=100.0,
        ),
        mandate=InvestmentMandate(
            max_drawdown_pct=15.0,
            horizon="Intraday to swing",
            max_position_pct=70.0,
        ),
        latest_performance_review="fake review content",
    )

    result = workflow.run_cycle(cycle_input)

    assert result.risk_assessment.is_approved is False
    assert result.execution_report.execution_status is ExecutionStatus.NOT_EXECUTED
    exchange_client.place_market_order.assert_not_called()
    exchange_client.place_limit_order.assert_not_called()
    exchange_client.cancel_order.assert_not_called()


def test_workflow_passes_oco_review_required_to_decision_maker() -> None:
    """Il workflow deve passare cycle_input.oco_review_required a DecisionMakerInput."""
    captured: dict[str, object] = {}

    class CapturingDM:
        def run(self, agent_input: DecisionMakerInput) -> TradeProposal:
            captured["oco_review_required"] = agent_input.oco_review_required
            return TradeProposal(
                action=TradeAction.BUY,
                order_type=OrderType.MARKET,
                confidence=0.8,
                reason="buy",
                details=TradeProposalDetails(quantity=0.001),
            )

    cycle_input = _make_cycle_input()
    cycle_input.oco_review_required = True

    workflow = TradingWorkflow(
        market_analyst=DummyMarketAnalyst([]),
        decision_maker=CapturingDM(),
        risk_manager=DummyRiskManager([]),
        execution_trader=DummyExecutionTrader([]),
    )
    workflow.run_cycle(cycle_input)

    assert captured["oco_review_required"] is True


def test_workflow_passes_current_price_to_decision_maker() -> None:
    """Il workflow deve passare market_data.price come current_price al DecisionMakerInput."""
    captured: dict[str, object] = {}

    class CapturingDecisionMaker:
        def run(self, agent_input: DecisionMakerInput) -> TradeProposal:
            captured["current_price"] = agent_input.current_price
            return TradeProposal(
                action=TradeAction.BUY,
                order_type=OrderType.MARKET,
                confidence=0.8,
                reason="buy signal",
                details=TradeProposalDetails(quantity=0.001),
            )

    workflow = TradingWorkflow(
        market_analyst=DummyMarketAnalyst([]),
        decision_maker=CapturingDecisionMaker(),
        risk_manager=DummyRiskManager([]),
        execution_trader=DummyExecutionTrader([]),
    )

    cycle_input = _make_cycle_input()  # price=100000.0
    workflow.run_cycle(cycle_input)

    assert captured["current_price"] == pytest.approx(100000.0)
