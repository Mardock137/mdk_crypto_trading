"""Test per _parse_market_analysis: casi validi, default opzionali, campi mancanti."""

from __future__ import annotations

import pytest

from src.agents.market_analyst import _parse_market_analysis
from src.core.contracts import MarketBias, SuggestedAction


# --- JSON valido BULLISH ---

def test_parse_bullish_signal() -> None:
    data = {
        "market_bias": "BULLISH",
        "signal_strength": 0.85,
        "confidence": 0.78,
        "summary": "Momentum rialzista confermato da RSI e MACD.",
        "key_factors": ["RSI sopra 60", "MACD positivo"],
        "risk_notes": ["Volume basso"],
        "suggested_action": "LONG_BIAS",
    }
    result = _parse_market_analysis(data)

    assert result.market_bias is MarketBias.BULLISH
    assert result.signal_strength == pytest.approx(0.85)
    assert result.confidence == pytest.approx(0.78)
    assert result.summary == "Momentum rialzista confermato da RSI e MACD."
    assert result.key_factors == ["RSI sopra 60", "MACD positivo"]
    assert result.risk_notes == ["Volume basso"]
    assert result.suggested_action is SuggestedAction.LONG_BIAS


# --- JSON valido NEUTRAL con NO_TRADE_BIAS ---

def test_parse_neutral_signal() -> None:
    data = {
        "market_bias": "NEUTRAL",
        "signal_strength": 0.4,
        "confidence": 0.55,
        "summary": "Mercato laterale senza direzione chiara.",
        "suggested_action": "NO_TRADE_BIAS",
    }
    result = _parse_market_analysis(data)

    assert result.market_bias is MarketBias.NEUTRAL
    assert result.signal_strength == pytest.approx(0.4)
    assert result.suggested_action is SuggestedAction.NO_TRADE_BIAS


# --- Campi opzionali assenti → default a liste vuote ---

def test_parse_missing_optional_fields_defaults_to_empty_lists() -> None:
    data = {
        "market_bias": "BEARISH",
        "signal_strength": 0.7,
        "confidence": 0.65,
        "summary": "Segnale ribassista.",
    }
    result = _parse_market_analysis(data)

    assert result.key_factors == []
    assert result.risk_notes == []


# --- suggested_action assente → default a NO_TRADE_BIAS ---

def test_parse_missing_suggested_action_defaults_to_no_trade_bias() -> None:
    data = {
        "market_bias": "BULLISH",
        "signal_strength": 0.6,
        "confidence": 0.7,
        "summary": "Segnale debole.",
    }
    result = _parse_market_analysis(data)

    assert result.suggested_action is SuggestedAction.NO_TRADE_BIAS


# --- Campi obbligatori mancanti ---

def test_parse_missing_required_fields_raises() -> None:
    data = {"market_bias": "BULLISH", "signal_strength": 0.8}
    with pytest.raises(ValueError, match="Campi mancanti"):
        _parse_market_analysis(data)
