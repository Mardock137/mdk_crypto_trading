"""Test per _parse_risk_assessment: 3 casi (APPROVE, BLOCK, REQUEST_ADJUSTMENT)."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, PropertyMock, patch

from src.agents.risk_manager import RiskManagerAgent, _parse_risk_assessment
from src.core.contracts import (
    MarketAnalysis,
    MarketBias,
    OperationConstraints,
    OrderType,
    PortfolioState,
    RiskDecision,
    RiskManagerInput,
    SuggestedAction,
    TradeAction,
    TradeProposal,
)


# --- APPROVE ---

def test_parse_approve() -> None:
    data = {
        "risk_decision": "APPROVE",
        "confidence": 0.91,
        "reason": "Proposta coerente con saldo disponibile.",
        "checks": [
            "Saldo sufficiente",
            "Quantita valida",
            "Nessun ordine in conflitto",
        ],
    }
    result = _parse_risk_assessment(data)

    assert result.risk_decision is RiskDecision.APPROVE
    assert result.is_approved is True
    assert result.confidence == pytest.approx(0.91)
    assert result.reason == "Proposta coerente con saldo disponibile."
    assert len(result.checks) == 3
    assert result.required_changes == []


# --- BLOCK ---

def test_parse_block() -> None:
    data = {
        "risk_decision": "BLOCK",
        "confidence": 0.96,
        "reason": "La quantita proposta supera quella realmente disponibile.",
        "checks": ["SELL superiore alla quantita libera"],
    }
    result = _parse_risk_assessment(data)

    assert result.risk_decision is RiskDecision.BLOCK
    assert result.is_approved is False
    assert result.confidence == pytest.approx(0.96)
    assert result.reason == "La quantita proposta supera quella realmente disponibile."
    assert len(result.checks) == 1
    assert result.required_changes == []


# --- REQUEST_ADJUSTMENT ---

def test_parse_request_adjustment() -> None:
    data = {
        "risk_decision": "REQUEST_ADJUSTMENT",
        "confidence": 0.88,
        "reason": "Valore stimato dell'ordine troppo basso.",
        "checks": ["Ordine sotto il minimo operativo"],
        "required_changes": ["Aumentare la quantita oppure scegliere HOLD"],
    }
    result = _parse_risk_assessment(data)

    assert result.risk_decision is RiskDecision.REQUEST_ADJUSTMENT
    assert result.is_approved is False
    assert result.confidence == pytest.approx(0.88)
    assert len(result.required_changes) == 1
    assert result.required_changes[0] == "Aumentare la quantita oppure scegliere HOLD"


# --- Campi opzionali assenti ---

def test_parse_defaults_for_optional_fields() -> None:
    data = {
        "risk_decision": "APPROVE",
        "confidence": 0.85,
        "reason": "Ok.",
    }
    result = _parse_risk_assessment(data)

    assert result.checks == []
    assert result.required_changes == []


# --- Campi mancanti ---

def test_parse_missing_fields_raises() -> None:
    data = {"risk_decision": "APPROVE"}
    with pytest.raises(ValueError, match="Campi mancanti"):
        _parse_risk_assessment(data)


# --- Risposta wrappata in array (comportamento Gemini reale) ---

def test_parse_array_wrapped_response() -> None:
    data = [
        {
            "risk_decision": "APPROVE",
            "confidence": 0.93,
            "reason": "Azione HOLD coerente con il contesto.",
            "checks": ["Azione HOLD valida"],
        }
    ]
    result = _parse_risk_assessment(data)

    assert result.risk_decision is RiskDecision.APPROVE
    assert result.confidence == pytest.approx(0.93)


# --- Risposta vuota ---

def test_parse_empty_dict_raises() -> None:
    with pytest.raises(ValueError, match="dict vuoto"):
        _parse_risk_assessment({})


# --- Retry su RuntimeError da generate_json ---

def _make_rm_input() -> RiskManagerInput:
    return RiskManagerInput(
        symbol="BTCUSDC",
        proposal=TradeProposal(
            action=TradeAction.HOLD,
            order_type=OrderType.NONE,
            confidence=0.7,
            reason="Mercato incerto.",
        ),
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
        "risk_decision": "APPROVE",
        "confidence": 0.9,
        "reason": "Proposta valida.",
        "checks": ["Saldo sufficiente"],
    }
    mock_llm.generate_json.side_effect = [
        RuntimeError("Risposta non valida"),
        valid_response,
    ]

    agent = RiskManagerAgent(llm=mock_llm)
    mock_prompt = MagicMock()
    mock_prompt.read_text.return_value = "system prompt"
    with patch("src.agents.risk_manager.time.sleep"):
        with patch.object(type(agent), "prompt_path", new_callable=PropertyMock, return_value=mock_prompt):
            result = agent.run(_make_rm_input())

    assert mock_llm.generate_json.call_count == 2
    assert result.risk_decision is RiskDecision.APPROVE


def test_agent_retries_up_to_4_times_then_raises() -> None:
    """Verifica che l'agente esegua esattamente 4 tentativi prima di propagare l'eccezione."""
    mock_llm = MagicMock()
    mock_llm.generate_json.side_effect = RuntimeError("Risposta non valida")

    agent = RiskManagerAgent(llm=mock_llm)
    mock_prompt = MagicMock()
    mock_prompt.read_text.return_value = "system prompt"
    with patch("src.agents.risk_manager.time.sleep"):
        with patch.object(type(agent), "prompt_path", new_callable=PropertyMock, return_value=mock_prompt):
            with pytest.raises(RuntimeError):
                agent.run(_make_rm_input())

    assert mock_llm.generate_json.call_count == 4


def test_agent_retry_backoff_sleep_values() -> None:
    """Verifica che il backoff tra i retry segua la progressione 4s, 8s, 16s."""
    mock_llm = MagicMock()
    mock_llm.generate_json.side_effect = RuntimeError("Risposta non valida")

    agent = RiskManagerAgent(llm=mock_llm)
    mock_prompt = MagicMock()
    mock_prompt.read_text.return_value = "system prompt"
    with patch("src.agents.risk_manager.time.sleep") as mock_sleep:
        with patch.object(type(agent), "prompt_path", new_callable=PropertyMock, return_value=mock_prompt):
            with pytest.raises(RuntimeError):
                agent.run(_make_rm_input())

    sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
    assert sleep_calls == [4, 8, 16]


def test_agent_warning_includes_raw_response() -> None:
    """Verifica che il WARNING del retry includa la risposta raw del LLM."""
    mock_llm = MagicMock()
    valid_response = {
        "risk_decision": "APPROVE",
        "confidence": 0.9,
        "reason": "Proposta valida.",
        "checks": ["Saldo sufficiente"],
    }
    mock_llm.generate_json.side_effect = [
        RuntimeError("Risposta non valida"),
        valid_response,
    ]

    agent = RiskManagerAgent(llm=mock_llm)
    mock_prompt = MagicMock()
    mock_prompt.read_text.return_value = "system prompt"
    with patch("src.agents.risk_manager.time.sleep"):
        with patch.object(type(agent), "prompt_path", new_callable=PropertyMock, return_value=mock_prompt):
            with patch.object(agent, "_logger") as mock_logger:
                agent.run(_make_rm_input())

    mock_logger.warning.assert_called_once()
    warning_args = mock_logger.warning.call_args.args
    assert "Risposta:" in warning_args[0]
