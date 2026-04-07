"""Test per _parse_risk_assessment: 3 casi (APPROVE, BLOCK, REQUEST_ADJUSTMENT)."""

from __future__ import annotations

import pytest

from src.agents.risk_manager import _parse_risk_assessment
from src.core.contracts import RiskDecision


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
