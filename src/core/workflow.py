from __future__ import annotations

from src.agents.decision_maker import DecisionMakerAgent
from src.agents.execution_trader import ExecutionTraderAgent
from src.agents.market_analyst import MarketAnalystAgent
from src.agents.risk_manager import RiskManagerAgent
from src.core.contracts import (
    DecisionMakerInput,
    ExecutionInput,
    MarketAnalystInput,
    RiskManagerInput,
    TradingCycleInput,
    TradingCycleResult,
)
from src.core.exceptions import CycleExecutionError


class TradingWorkflow:
    def __init__(
        self,
        market_analyst: MarketAnalystAgent,
        decision_maker: DecisionMakerAgent,
        risk_manager: RiskManagerAgent,
        execution_trader: ExecutionTraderAgent,
    ) -> None:
        self.market_analyst = market_analyst
        self.decision_maker = decision_maker
        self.risk_manager = risk_manager
        self.execution_trader = execution_trader

    def run_cycle(self, cycle_input: TradingCycleInput) -> TradingCycleResult:
        # Il workflow resta intenzionalmente semplice: una catena lineare e testabile.
        # Ogni step viene avvolto in try/except così, se fallisce, il runner può
        # salvare nel log eventi gli output parziali già prodotti.
        try:
            market_analysis = self.market_analyst.run(
                MarketAnalystInput(
                    symbol=cycle_input.symbol,
                    market_data=cycle_input.market_data,
                )
            )
        except Exception as exc:
            raise CycleExecutionError(
                f"Market Analyst failed: {exc}",
                original=exc,
            ) from exc

        try:
            trade_proposal = self.decision_maker.run(
                DecisionMakerInput(
                    symbol=cycle_input.symbol,
                    portfolio=cycle_input.portfolio,
                    market_analysis=market_analysis,
                    constraints=cycle_input.constraints,
                    mandate=cycle_input.mandate,
                    decision_memory=cycle_input.decision_memory,
                    performance_summary=cycle_input.performance_summary,
                    recent_performance=cycle_input.recent_performance,
                    latest_performance_review=cycle_input.latest_performance_review,
                    current_price=cycle_input.market_data.price,
                    oco_review_required=cycle_input.oco_review_required,
                )
            )
        except Exception as exc:
            raise CycleExecutionError(
                f"Decision Maker failed: {exc}",
                original=exc,
                market_analysis=market_analysis,
            ) from exc

        try:
            risk_assessment = self.risk_manager.run(
                RiskManagerInput(
                    symbol=cycle_input.symbol,
                    proposal=trade_proposal,
                    portfolio=cycle_input.portfolio,
                    market_analysis=market_analysis,
                    constraints=cycle_input.constraints,
                    current_price=cycle_input.market_data.price,
                )
            )
        except Exception as exc:
            raise CycleExecutionError(
                f"Risk Manager failed: {exc}",
                original=exc,
                market_analysis=market_analysis,
                trade_proposal=trade_proposal,
            ) from exc

        try:
            execution_report = self.execution_trader.run(
                ExecutionInput(
                    symbol=cycle_input.symbol,
                    proposal=trade_proposal,
                    risk_assessment=risk_assessment,
                    portfolio=cycle_input.portfolio,
                    mandate=cycle_input.mandate,
                    max_order_notional_usdc=cycle_input.constraints.max_order_notional_usdc,
                    current_price=cycle_input.market_data.price,
                    min_order_usdc=cycle_input.constraints.min_order_usdc,
                )
            )
        except Exception as exc:
            raise CycleExecutionError(
                f"Execution Trader failed: {exc}",
                original=exc,
                market_analysis=market_analysis,
                trade_proposal=trade_proposal,
                risk_assessment=risk_assessment,
            ) from exc

        return TradingCycleResult(
            market_analysis=market_analysis,
            trade_proposal=trade_proposal,
            risk_assessment=risk_assessment,
            execution_report=execution_report,
        )

