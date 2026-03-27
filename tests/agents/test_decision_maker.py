"""Test per _parse_trade_proposal: 4 casi (BUY MARKET, SELL LIMIT, HOLD, CANCEL_AND_REPLACE_ORDER)."""

from __future__ import annotations

import pytest

from src.agents.decision_maker import _parse_trade_proposal
from src.core.contracts import OrderSide, OrderType, TradeAction


# --- BUY MARKET ---

def test_parse_buy_market() -> None:
    data = {
        "action": "BUY",
        "order_type": "MARKET",
        "confidence": 0.82,
        "reason": "segnale rialzista forte",
        "details": {"quantity": 0.001},
    }
    result = _parse_trade_proposal(data)

    assert result.action is TradeAction.BUY
    assert result.order_type is OrderType.MARKET
    assert result.confidence == pytest.approx(0.82)
    assert result.reason == "segnale rialzista forte"
    assert result.details.quantity == pytest.approx(0.001)
    assert result.details.price is None
    assert result.details.order_id is None
    assert result.details.side is None


# --- SELL LIMIT ---

def test_parse_sell_limit() -> None:
    data = {
        "action": "SELL",
        "order_type": "LIMIT",
        "confidence": 0.76,
        "reason": "resistenza vicina",
        "details": {"quantity": 0.001, "price": 98500},
    }
    result = _parse_trade_proposal(data)

    assert result.action is TradeAction.SELL
    assert result.order_type is OrderType.LIMIT
    assert result.confidence == pytest.approx(0.76)
    assert result.reason == "resistenza vicina"
    assert result.details.quantity == pytest.approx(0.001)
    assert result.details.price == pytest.approx(98500)
    assert result.details.order_id is None
    assert result.details.side is None


# --- HOLD ---

def test_parse_hold() -> None:
    data = {
        "action": "HOLD",
        "order_type": "NONE",
        "confidence": 0.64,
        "reason": "dati insufficienti",
        "details": {},
    }
    result = _parse_trade_proposal(data)

    assert result.action is TradeAction.HOLD
    assert result.order_type is OrderType.NONE
    assert result.confidence == pytest.approx(0.64)
    assert result.reason == "dati insufficienti"
    assert result.is_hold is True
    assert result.details.quantity is None
    assert result.details.price is None


# --- CANCEL_AND_REPLACE_ORDER ---

def test_parse_cancel_and_replace_order() -> None:
    data = {
        "action": "CANCEL_AND_REPLACE_ORDER",
        "order_type": "LIMIT",
        "confidence": 0.71,
        "reason": "prezzo migliorato",
        "details": {
            "order_id": "123456789",
            "side": "BUY",
            "quantity": 0.001,
            "price": 97250,
        },
    }
    result = _parse_trade_proposal(data)

    assert result.action is TradeAction.CANCEL_AND_REPLACE_ORDER
    assert result.order_type is OrderType.LIMIT
    assert result.confidence == pytest.approx(0.71)
    assert result.reason == "prezzo migliorato"
    assert result.details.order_id == "123456789"
    assert result.details.side is OrderSide.BUY
    assert result.details.quantity == pytest.approx(0.001)
    assert result.details.price == pytest.approx(97250)


# --- Campi mancanti ---

def test_parse_missing_fields_raises() -> None:
    data = {"action": "BUY", "order_type": "MARKET"}
    with pytest.raises(ValueError, match="Campi mancanti"):
        _parse_trade_proposal(data)
