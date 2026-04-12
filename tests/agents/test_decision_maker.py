"""Test per _parse_trade_proposal: 4 casi (BUY MARKET, SELL LIMIT, HOLD, CANCEL_AND_REPLACE_ORDER)."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, PropertyMock, patch

from src.agents.decision_maker import DecisionMakerAgent, _parse_trade_proposal
from src.core.contracts import (
    DecisionMakerInput,
    MarketAnalysis,
    MarketBias,
    OperationConstraints,
    OrderSide,
    OrderType,
    PortfolioState,
    SuggestedAction,
    TradeAction,
)


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


# --- Risposta wrappata in array ---

def test_parse_array_wrapped_response() -> None:
    data = [
        {
            "action": "HOLD",
            "order_type": "NONE",
            "confidence": 0.72,
            "reason": "Mercato incerto.",
            "details": {},
        }
    ]
    result = _parse_trade_proposal(data)

    assert result.action is TradeAction.HOLD
    assert result.confidence == pytest.approx(0.72)


# --- Risposta vuota ---

def test_parse_empty_dict_raises() -> None:
    with pytest.raises(ValueError, match="dict vuoto"):
        _parse_trade_proposal({})


# --- Retry su RuntimeError da generate_json ---

def _make_dm_input() -> DecisionMakerInput:
    return DecisionMakerInput(
        symbol="BTCUSDC",
        portfolio=PortfolioState(
            usdc_balance=500.0,
            usdc_balance_total=500.0,
            usdc_value=0.0,
            portfolio_qty_free=0.0,
            portfolio_qty_total=0.0,
        ),
        market_analysis=MarketAnalysis(
            market_bias=MarketBias.NEUTRAL,
            signal_strength=0.5,
            confidence=0.5,
            summary="Neutrale.",
            suggested_action=SuggestedAction.NO_TRADE_BIAS,
        ),
        constraints=OperationConstraints(cycle_interval_seconds=3600, min_order_usdc=10.0),
    )


def test_agent_retries_on_runtime_error_then_succeeds() -> None:
    """Verifica che l'agente riprovi se generate_json lancia RuntimeError al primo tentativo."""
    mock_llm = MagicMock()
    valid_response = {
        "action": "HOLD",
        "order_type": "NONE",
        "confidence": 0.7,
        "reason": "Mercato incerto.",
        "details": {},
    }
    mock_llm.generate_json.side_effect = [
        RuntimeError("Risposta non valida"),
        valid_response,
    ]

    agent = DecisionMakerAgent(llm=mock_llm)
    mock_prompt = MagicMock()
    mock_prompt.read_text.return_value = "system prompt"
    with patch("src.agents.decision_maker.time.sleep"):
        with patch.object(type(agent), "prompt_path", new_callable=PropertyMock, return_value=mock_prompt):
            result = agent.run(_make_dm_input())

    assert mock_llm.generate_json.call_count == 2
    assert result.action is TradeAction.HOLD


def test_agent_retries_up_to_4_times_then_raises() -> None:
    """Verifica che l'agente esegua esattamente 4 tentativi prima di propagare l'eccezione."""
    mock_llm = MagicMock()
    mock_llm.generate_json.side_effect = RuntimeError("Risposta non valida")

    agent = DecisionMakerAgent(llm=mock_llm)
    mock_prompt = MagicMock()
    mock_prompt.read_text.return_value = "system prompt"
    with patch("src.agents.decision_maker.time.sleep"):
        with patch.object(type(agent), "prompt_path", new_callable=PropertyMock, return_value=mock_prompt):
            with pytest.raises(RuntimeError):
                agent.run(_make_dm_input())

    assert mock_llm.generate_json.call_count == 4


def test_agent_retry_backoff_sleep_values() -> None:
    """Verifica che il backoff tra i retry segua la progressione 4s, 8s, 16s."""
    mock_llm = MagicMock()
    mock_llm.generate_json.side_effect = RuntimeError("Risposta non valida")

    agent = DecisionMakerAgent(llm=mock_llm)
    mock_prompt = MagicMock()
    mock_prompt.read_text.return_value = "system prompt"
    with patch("src.agents.decision_maker.time.sleep") as mock_sleep:
        with patch.object(type(agent), "prompt_path", new_callable=PropertyMock, return_value=mock_prompt):
            with pytest.raises(RuntimeError):
                agent.run(_make_dm_input())

    sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
    assert sleep_calls == [4, 8, 16]


def test_agent_warning_includes_raw_response() -> None:
    """Verifica che il WARNING del retry includa la risposta raw del LLM."""
    mock_llm = MagicMock()
    valid_response = {
        "action": "HOLD",
        "order_type": "NONE",
        "confidence": 0.7,
        "reason": "Mercato incerto.",
        "details": {},
    }
    mock_llm.generate_json.side_effect = [
        RuntimeError("Risposta non valida"),
        valid_response,
    ]

    agent = DecisionMakerAgent(llm=mock_llm)
    mock_prompt = MagicMock()
    mock_prompt.read_text.return_value = "system prompt"
    with patch("src.agents.decision_maker.time.sleep"):
        with patch.object(type(agent), "prompt_path", new_callable=PropertyMock, return_value=mock_prompt):
            with patch.object(agent, "_logger") as mock_logger:
                agent.run(_make_dm_input())

    mock_logger.warning.assert_called_once()
    warning_args = mock_logger.warning.call_args.args
    assert "Risposta:" in warning_args[0]
