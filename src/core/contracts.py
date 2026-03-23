from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MarketBias(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class SuggestedAction(str, Enum):
    LONG_BIAS = "LONG_BIAS"
    SHORT_BIAS = "SHORT_BIAS"
    NO_TRADE_BIAS = "NO_TRADE_BIAS"


class TradeAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CANCEL_AND_REPLACE_ORDER = "CANCEL_AND_REPLACE_ORDER"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    NONE = "NONE"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class RiskDecision(str, Enum):
    APPROVE = "APPROVE"
    BLOCK = "BLOCK"
    REQUEST_ADJUSTMENT = "REQUEST_ADJUSTMENT"


class ExecutionStatus(str, Enum):
    EXECUTED = "EXECUTED"
    NOT_EXECUTED = "NOT_EXECUTED"
    FAILED = "FAILED"


@dataclass(slots=True)
class MarketDataSnapshot:
    symbol: str
    price: float | None = None
    avg_price: float | None = None
    volume_24h: float | None = None
    recent_public_trades: list[dict[str, Any]] = field(default_factory=list)
    order_book_top_10_bids: list[dict[str, Any]] = field(default_factory=list)
    order_book_top_10_asks: list[dict[str, Any]] = field(default_factory=list)
    indicators: dict[str, float | None] = field(default_factory=dict)
    candles: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PortfolioState:
    usdc_balance: float
    usdc_balance_total: float
    usdc_value: float
    portfolio_qty_free: float
    portfolio_qty_total: float
    portfolio_snapshot: str = ""
    open_orders: list[dict[str, Any]] = field(default_factory=list)
    last_trades: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class OperationConstraints:
    cycle_interval_seconds: int
    min_order_usdc: float


@dataclass(slots=True)
class MarketAnalysis:
    market_bias: MarketBias
    signal_strength: float
    confidence: float
    summary: str
    key_factors: list[str] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)
    suggested_action: SuggestedAction = SuggestedAction.NO_TRADE_BIAS


@dataclass(slots=True)
class TradeProposalDetails:
    quantity: float | None = None
    price: float | None = None
    order_id: str | None = None
    side: OrderSide | None = None

    def estimated_notional(self, reference_price: float | None = None) -> float | None:
        if self.quantity is None:
            return None

        effective_price = self.price if self.price is not None else reference_price
        if effective_price is None:
            return None

        return self.quantity * effective_price


@dataclass(slots=True)
class TradeProposal:
    action: TradeAction
    order_type: OrderType
    confidence: float
    reason: str
    details: TradeProposalDetails = field(default_factory=TradeProposalDetails)

    @property
    def is_hold(self) -> bool:
        return self.action is TradeAction.HOLD


@dataclass(slots=True)
class RiskAssessment:
    risk_decision: RiskDecision
    confidence: float
    reason: str
    checks: list[str] = field(default_factory=list)
    required_changes: list[str] = field(default_factory=list)

    @property
    def is_approved(self) -> bool:
        return self.risk_decision is RiskDecision.APPROVE


@dataclass(slots=True)
class ExecutionReport:
    execution_status: ExecutionStatus
    executed_action: TradeAction
    order_type: OrderType
    reason: str
    execution_details: dict[str, Any] = field(default_factory=dict)

    @property
    def was_executed(self) -> bool:
        return self.execution_status is ExecutionStatus.EXECUTED


@dataclass(slots=True)
class MarketAnalystInput:
    symbol: str
    market_data: MarketDataSnapshot


@dataclass(slots=True)
class DecisionMakerInput:
    symbol: str
    portfolio: PortfolioState
    market_analysis: MarketAnalysis
    constraints: OperationConstraints
    ia_memory: list[dict[str, Any]] = field(default_factory=list)
    performance_summary: str = ""
    recent_performance: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class RiskManagerInput:
    symbol: str
    proposal: TradeProposal
    portfolio: PortfolioState
    market_analysis: MarketAnalysis
    constraints: OperationConstraints
    current_price: float | None = None


@dataclass(slots=True)
class ExecutionInput:
    symbol: str
    proposal: TradeProposal
    risk_assessment: RiskAssessment
    portfolio: PortfolioState
    constraints: OperationConstraints
    current_price: float | None = None


@dataclass(slots=True)
class TradingCycleInput:
    symbol: str
    market_data: MarketDataSnapshot
    portfolio: PortfolioState
    constraints: OperationConstraints
    ia_memory: list[dict[str, Any]] = field(default_factory=list)
    performance_summary: str = ""
    recent_performance: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class TradingCycleResult:
    market_analysis: MarketAnalysis
    trade_proposal: TradeProposal
    risk_assessment: RiskAssessment
    execution_report: ExecutionReport

