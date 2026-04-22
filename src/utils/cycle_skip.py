"""Pre-check deterministico che decide se saltare un ciclo operativo.

Confronta il contesto attuale (mercato + portafoglio) con lo snapshot del ciclo
precedente. Se nulla di rilevante e' cambiato ed e' legittimo farlo, ritorna
``(True, reason)`` in modo che il runner possa evitare di chiamare gli agenti
LLM (risparmio di token + latenza).
"""
from __future__ import annotations

from typing import Any

from src.core.contracts import (
    CycleContextSnapshot,
    CycleSkipConfig,
    MarketDataSnapshot,
    PortfolioState,
    TradeAction,
)


def extract_open_order_ids(portfolio: PortfolioState) -> set[str]:
    """Estrae l'insieme degli ``orderId`` dagli ordini aperti del portafoglio."""
    ids: set[str] = set()
    for order in portfolio.open_orders:
        order_id = _get_order_id(order)
        if order_id is not None:
            ids.add(order_id)
    return ids


def should_skip_cycle(
    previous: CycleContextSnapshot | None,
    current_market: MarketDataSnapshot,
    current_portfolio: PortfolioState,
    config: CycleSkipConfig,
    consecutive_skips: int,
) -> tuple[bool, str]:
    """Ritorna ``(True, reason)`` se il ciclo puo' essere saltato in sicurezza.

    Caso ``previous is None`` (primo ciclo) → ``(False, "no previous context")``.
    Caso counter al massimo → ``(False, "max consecutive skips reached")``.
    """
    if not config.enabled:
        return False, "cycle skip disabled"

    if previous is None:
        return False, "no previous context"

    if consecutive_skips >= config.max_consecutive_skips:
        return False, "max consecutive skips reached"

    if config.require_previous_action_hold and previous.previous_action is not TradeAction.HOLD:
        return False, f"previous action was {previous.previous_action.value}, not HOLD"

    current_ids = extract_open_order_ids(current_portfolio)
    if config.require_no_order_events and current_ids != previous.open_order_ids:
        return False, "open orders set changed since last cycle"

    current_price = current_market.price
    previous_price = previous.price
    if current_price is None or previous_price is None or previous_price == 0:
        return False, "price unavailable for comparison"

    price_delta_pct = abs((current_price - previous_price) / previous_price) * 100.0
    if price_delta_pct > config.price_delta_pct:
        return (
            False,
            f"price moved {price_delta_pct:.2f}% > {config.price_delta_pct}%",
        )

    current_rsi = _get_indicator(current_market, "rsi")
    previous_rsi = previous.rsi
    if current_rsi is not None and previous_rsi is not None:
        if abs(current_rsi - previous_rsi) > config.rsi_delta:
            return (
                False,
                f"RSI delta {abs(current_rsi - previous_rsi):.2f} > {config.rsi_delta}",
            )

    if config.macd_sign_must_match:
        current_macd = _get_indicator(current_market, "macd")
        current_macd_signal = _get_indicator(current_market, "macd_signal")
        previous_macd = previous.macd
        previous_macd_signal = previous.macd_signal
        if (
            current_macd is not None
            and previous_macd is not None
            and current_macd_signal is not None
            and previous_macd_signal is not None
        ):
            current_sign = _macd_sign(current_macd, current_macd_signal)
            previous_sign = _macd_sign(previous_macd, previous_macd_signal)
            if current_sign != previous_sign:
                return False, "MACD sign changed since last cycle"

    return True, "context unchanged within thresholds"


def _get_indicator(market: MarketDataSnapshot, key: str) -> float | None:
    value = market.indicators.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_order_id(order: dict[str, Any]) -> str | None:
    for key in ("orderId", "order_id", "id"):
        value = order.get(key)
        if value is not None:
            return str(value)
    return None


def _macd_sign(macd: float, signal: float) -> int:
    diff = macd - signal
    if diff > 0:
        return 1
    if diff < 0:
        return -1
    return 0
