from __future__ import annotations

from src.core.contracts import (
    CycleContextSnapshot,
    CycleSkipConfig,
    MarketDataSnapshot,
    PortfolioState,
    TradeAction,
)
from src.utils.cycle_skip import extract_open_order_ids, should_skip_cycle


def _make_config(
    enabled: bool = True,
    max_consecutive_skips: int = 4,
    price_delta_pct: float = 0.5,
    rsi_delta: float = 2.0,
    macd_sign_must_match: bool = True,
    require_no_order_events: bool = True,
    require_previous_action_hold: bool = True,
) -> CycleSkipConfig:
    return CycleSkipConfig(
        enabled=enabled,
        max_consecutive_skips=max_consecutive_skips,
        price_delta_pct=price_delta_pct,
        rsi_delta=rsi_delta,
        macd_sign_must_match=macd_sign_must_match,
        require_no_order_events=require_no_order_events,
        require_previous_action_hold=require_previous_action_hold,
    )


def _make_snapshot(
    price: float = 100.0,
    rsi: float = 50.0,
    macd: float = 1.0,
    macd_signal: float = 0.5,
    previous_action: TradeAction = TradeAction.HOLD,
    open_order_ids: set[str] | None = None,
) -> CycleContextSnapshot:
    return CycleContextSnapshot(
        price=price,
        rsi=rsi,
        macd=macd,
        macd_signal=macd_signal,
        previous_action=previous_action,
        open_order_ids=open_order_ids or set(),
    )


def _make_market(
    price: float = 100.0,
    rsi: float = 50.0,
    macd: float = 1.0,
    macd_signal: float = 0.5,
) -> MarketDataSnapshot:
    return MarketDataSnapshot(
        symbol="BTCUSDC",
        price=price,
        indicators={"rsi": rsi, "macd": macd, "macd_signal": macd_signal},
    )


def _make_portfolio(open_orders: list[dict] | None = None) -> PortfolioState:
    return PortfolioState(
        usdc_balance=1000.0,
        usdc_balance_total=1000.0,
        usdc_value=1000.0,
        portfolio_qty_free=0.0,
        portfolio_qty_total=0.0,
        open_orders=open_orders or [],
    )


def test_disabled_returns_false() -> None:
    result, reason = should_skip_cycle(
        previous=_make_snapshot(),
        current_market=_make_market(),
        current_portfolio=_make_portfolio(),
        config=_make_config(enabled=False),
        consecutive_skips=0,
    )
    assert result is False
    assert "disabled" in reason


def test_first_cycle_returns_false() -> None:
    result, reason = should_skip_cycle(
        previous=None,
        current_market=_make_market(),
        current_portfolio=_make_portfolio(),
        config=_make_config(),
        consecutive_skips=0,
    )
    assert result is False
    assert "no previous context" in reason


def test_max_skips_reached_returns_false() -> None:
    result, reason = should_skip_cycle(
        previous=_make_snapshot(),
        current_market=_make_market(),
        current_portfolio=_make_portfolio(),
        config=_make_config(max_consecutive_skips=3),
        consecutive_skips=3,
    )
    assert result is False
    assert "max consecutive skips" in reason


def test_context_unchanged_returns_true() -> None:
    result, reason = should_skip_cycle(
        previous=_make_snapshot(),
        current_market=_make_market(),
        current_portfolio=_make_portfolio(),
        config=_make_config(),
        consecutive_skips=0,
    )
    assert result is True
    assert "unchanged" in reason


def test_previous_action_not_hold_returns_false() -> None:
    result, reason = should_skip_cycle(
        previous=_make_snapshot(previous_action=TradeAction.BUY),
        current_market=_make_market(),
        current_portfolio=_make_portfolio(),
        config=_make_config(),
        consecutive_skips=0,
    )
    assert result is False
    assert "HOLD" in reason


def test_open_orders_changed_returns_false() -> None:
    result, reason = should_skip_cycle(
        previous=_make_snapshot(open_order_ids={"1"}),
        current_market=_make_market(),
        current_portfolio=_make_portfolio(open_orders=[{"orderId": "2"}]),
        config=_make_config(),
        consecutive_skips=0,
    )
    assert result is False
    assert "open orders" in reason


def test_price_delta_over_threshold_returns_false() -> None:
    result, reason = should_skip_cycle(
        previous=_make_snapshot(price=100.0),
        current_market=_make_market(price=101.0),
        current_portfolio=_make_portfolio(),
        config=_make_config(price_delta_pct=0.5),
        consecutive_skips=0,
    )
    assert result is False
    assert "price moved" in reason


def test_rsi_delta_over_threshold_returns_false() -> None:
    result, reason = should_skip_cycle(
        previous=_make_snapshot(rsi=50.0),
        current_market=_make_market(rsi=55.0),
        current_portfolio=_make_portfolio(),
        config=_make_config(rsi_delta=2.0),
        consecutive_skips=0,
    )
    assert result is False
    assert "RSI delta" in reason


def test_rsi_check_is_skipped_when_both_values_are_none() -> None:
    result, reason = should_skip_cycle(
        previous=_make_snapshot(rsi=None),
        current_market=_make_market(rsi=None),
        current_portfolio=_make_portfolio(),
        config=_make_config(rsi_delta=2.0),
        consecutive_skips=0,
    )
    assert result is True
    assert "unchanged" in reason


def test_macd_sign_flip_returns_false() -> None:
    result, reason = should_skip_cycle(
        previous=_make_snapshot(macd=1.0, macd_signal=0.5),
        current_market=_make_market(macd=0.3, macd_signal=0.5),
        current_portfolio=_make_portfolio(),
        config=_make_config(),
        consecutive_skips=0,
    )
    assert result is False
    assert "MACD" in reason


def test_macd_sign_check_disabled() -> None:
    result, _ = should_skip_cycle(
        previous=_make_snapshot(macd=1.0, macd_signal=0.5),
        current_market=_make_market(macd=0.3, macd_signal=0.5),
        current_portfolio=_make_portfolio(),
        config=_make_config(macd_sign_must_match=False),
        consecutive_skips=0,
    )
    assert result is True


def test_price_missing_returns_false() -> None:
    result, reason = should_skip_cycle(
        previous=_make_snapshot(price=None),
        current_market=_make_market(),
        current_portfolio=_make_portfolio(),
        config=_make_config(),
        consecutive_skips=0,
    )
    assert result is False
    assert "price" in reason


def test_extract_open_order_ids_supports_variants() -> None:
    portfolio = _make_portfolio(
        open_orders=[
            {"orderId": "1"},
            {"order_id": "2"},
            {"id": "3"},
            {"foo": "bar"},
        ]
    )
    assert extract_open_order_ids(portfolio) == {"1", "2", "3"}
