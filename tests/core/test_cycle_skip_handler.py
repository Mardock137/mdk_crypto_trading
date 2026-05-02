from __future__ import annotations

import logging
import math
from unittest.mock import MagicMock

import pytest

from src.core.contracts import (
    CycleContextSnapshot,
    CycleSkipConfig,
    MarketDataSnapshot,
    PortfolioState,
    TradeAction,
)
from src.core.cycle_skip_handler import CycleSkipHandler, _coerce_float


_ENABLED_CONFIG = CycleSkipConfig(
    enabled=True,
    max_consecutive_skips=4,
    price_delta_pct=0.5,
    rsi_delta=2.0,
    macd_sign_must_match=True,
    require_no_order_events=True,
    require_previous_action_hold=True,
)

_DISABLED_CONFIG = CycleSkipConfig(
    enabled=False,
    max_consecutive_skips=4,
    price_delta_pct=0.5,
    rsi_delta=2.0,
    macd_sign_must_match=True,
    require_no_order_events=True,
    require_previous_action_hold=True,
)


def _market() -> MarketDataSnapshot:
    return MarketDataSnapshot(
        symbol="BTCUSDC",
        price=100.0,
        indicators={"rsi": 50.0, "macd": 1.0, "macd_signal": 0.5},
    )


def _portfolio() -> PortfolioState:
    return PortfolioState(
        usdc_balance=1000.0,
        usdc_balance_total=1000.0,
        usdc_value=1000.0,
        portfolio_qty_free=0.0,
        portfolio_qty_total=0.0,
        open_orders=[],
    )


def _make_handler(config: CycleSkipConfig) -> tuple[CycleSkipHandler, MagicMock]:
    event_logger = MagicMock()
    handler = CycleSkipHandler(
        symbol="BTCUSDC",
        trading_mode="DEMO",
        config=config,
        event_logger=event_logger,
        logger=logging.getLogger("mdk_crypto_trading.test_cycle_skip_handler"),
    )
    return handler, event_logger


def test_try_skip_returns_false_when_config_disabled() -> None:
    handler, event_logger = _make_handler(_DISABLED_CONFIG)

    assert handler.try_skip(_market(), _portfolio()) is False
    event_logger.log_skipped_cycle.assert_not_called()


def test_try_skip_returns_false_on_first_cycle() -> None:
    """Senza snapshot precedente non si può saltare."""
    handler, event_logger = _make_handler(_ENABLED_CONFIG)

    assert handler.try_skip(_market(), _portfolio()) is False
    event_logger.log_skipped_cycle.assert_not_called()


def test_try_skip_returns_true_when_context_unchanged() -> None:
    handler, event_logger = _make_handler(_ENABLED_CONFIG)
    handler._previous_snapshot = CycleContextSnapshot(
        price=100.0,
        rsi=50.0,
        macd=1.0,
        macd_signal=0.5,
        previous_action=TradeAction.HOLD,
        open_order_ids=set(),
    )

    assert handler.try_skip(_market(), _portfolio()) is True
    event_logger.log_skipped_cycle.assert_called_once()
    assert handler._consecutive_skips == 1


def test_record_completed_cycle_resets_counter_and_stores_snapshot() -> None:
    handler, _ = _make_handler(_ENABLED_CONFIG)
    handler._consecutive_skips = 3

    handler.record_completed_cycle(
        market_data=_market(),
        portfolio=_portfolio(),
        proposed_action=TradeAction.BUY,
    )

    assert handler._consecutive_skips == 0
    assert handler._previous_snapshot is not None
    assert handler._previous_snapshot.price == 100.0
    assert handler._previous_snapshot.rsi == 50.0
    assert handler._previous_snapshot.previous_action is TradeAction.BUY


def test_record_completed_cycle_handles_missing_indicators() -> None:
    """Indicatori mancanti o non numerici vengono coercizzati a None."""
    handler, _ = _make_handler(_ENABLED_CONFIG)
    market = MarketDataSnapshot(
        symbol="BTCUSDC",
        price=100.0,
        indicators={"rsi": None, "macd": "not-a-number"},
    )

    handler.record_completed_cycle(
        market_data=market,
        portfolio=_portfolio(),
        proposed_action=TradeAction.HOLD,
    )

    assert handler._previous_snapshot is not None
    assert handler._previous_snapshot.rsi is None
    assert handler._previous_snapshot.macd is None
    assert handler._previous_snapshot.macd_signal is None


def test_coerce_float_returns_none_for_nan() -> None:
    assert _coerce_float(math.nan) is None


def test_record_completed_cycle_warns_when_rsi_is_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    handler, _ = _make_handler(_ENABLED_CONFIG)
    market = MarketDataSnapshot(
        symbol="BTCUSDC",
        price=100.0,
        indicators={"rsi": None, "macd": 1.0, "macd_signal": 0.5},
    )

    with caplog.at_level(
        logging.WARNING,
        logger="mdk_crypto_trading.test_cycle_skip_handler",
    ):
        handler.record_completed_cycle(
            market_data=market,
            portfolio=_portfolio(),
            proposed_action=TradeAction.HOLD,
        )

    assert "rsi_delta guard is disabled" in caplog.text
