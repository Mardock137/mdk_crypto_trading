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


class MandateAdherence(str, Enum):
    ALIGNED = "ALIGNED"
    DRIFTING = "DRIFTING"
    MISALIGNED = "MISALIGNED"


@dataclass(slots=True)
class MarketDataSnapshot:
    symbol: str
    price: float | None = None
    avg_price: float | None = None
    volume_24h: float | None = None
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
class InvestmentMandate:
    """Mandato operativo: vincoli di rischio e contesto strategico imposti al Decision Maker."""

    max_drawdown_pct: float
    horizon: str
    max_position_pct: float


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
class PerformanceStats:
    """Statistiche deterministiche calcolate dai cicli recenti (zero LLM)."""

    period_start: str
    period_end: str
    total_cycles: int
    buy_executed: int
    sell_executed: int
    hold_count: int
    sell_failed: int
    hold_ratio: float
    strong_bullish_ignored: int
    strong_bearish_ignored: int
    realized_pnl_usdc: float
    avg_pnl_pct: float
    days_without_executed_trade: int


@dataclass(slots=True)
class PerformanceReview:
    """Giudizio qualitativo prodotto dal Performance Reviewer (LLM)."""

    summary: str
    mandate_adherence: MandateAdherence
    suggestions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MarketAnalystInput:
    symbol: str
    market_data: MarketDataSnapshot


@dataclass(slots=True)
class PerformanceReviewerInput:
    symbol: str
    mandate: InvestmentMandate
    stats: PerformanceStats
    days_analyzed: int


@dataclass(slots=True)
class DecisionMakerInput:
    symbol: str
    portfolio: PortfolioState
    market_analysis: MarketAnalysis
    constraints: OperationConstraints
    mandate: InvestmentMandate
    decision_memory: list[dict[str, Any]] = field(default_factory=list)
    performance_summary: str = ""
    recent_performance: list[dict[str, Any]] = field(default_factory=list)
    latest_performance_review: str = ""


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


@dataclass(slots=True)
class TradingCycleInput:
    symbol: str
    market_data: MarketDataSnapshot
    portfolio: PortfolioState
    constraints: OperationConstraints
    mandate: InvestmentMandate
    decision_memory: list[dict[str, Any]] = field(default_factory=list)
    performance_summary: str = ""
    recent_performance: list[dict[str, Any]] = field(default_factory=list)
    latest_performance_review: str = ""


@dataclass(slots=True)
class TradingCycleResult:
    market_analysis: MarketAnalysis
    trade_proposal: TradeProposal
    risk_assessment: RiskAssessment
    execution_report: ExecutionReport


@dataclass(frozen=True, slots=True)
class CycleSkipConfig:
    """Configurazione del pre-check deterministico che salta cicli non necessari."""

    enabled: bool
    max_consecutive_skips: int
    price_delta_pct: float
    rsi_delta: float
    macd_sign_must_match: bool
    require_no_order_events: bool
    require_previous_action_hold: bool


@dataclass(slots=True)
class CycleContextSnapshot:
    """Istantanea del contesto del ciclo precedente per confronti deterministici."""

    price: float | None
    rsi: float | None
    macd: float | None
    macd_signal: float | None
    previous_action: TradeAction
    open_order_ids: set[str] = field(default_factory=set)

