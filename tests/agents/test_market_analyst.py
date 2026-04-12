"""Test per _parse_market_analysis: casi validi, default opzionali, campi mancanti."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, PropertyMock, patch

from src.agents.market_analyst import MarketAnalystAgent, _parse_market_analysis
from src.core.contracts import MarketBias, MarketDataSnapshot, MarketAnalystInput, SuggestedAction


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


# --- Risposta wrappata in array ---

def test_parse_array_wrapped_response() -> None:
    data = [
        {
            "market_bias": "BULLISH",
            "signal_strength": 0.85,
            "confidence": 0.78,
            "summary": "Segnale rialzista.",
        }
    ]
    result = _parse_market_analysis(data)

    assert result.market_bias is MarketBias.BULLISH
    assert result.signal_strength == pytest.approx(0.85)


# --- Risposta vuota ---

def test_parse_empty_dict_raises() -> None:
    with pytest.raises(ValueError, match="dict vuoto"):
        _parse_market_analysis({})


# --- Retry su RuntimeError da generate_json ---

def test_agent_retries_on_runtime_error_then_succeeds() -> None:
    """Verifica che l'agente riprovi se generate_json lancia RuntimeError al primo tentativo."""
    mock_llm = MagicMock()
    valid_response = {
        "market_bias": "BULLISH",
        "signal_strength": 0.8,
        "confidence": 0.75,
        "summary": "Segnale rialzista.",
    }
    mock_llm.generate_json.side_effect = [
        RuntimeError("Risposta non valida"),
        valid_response,
    ]

    agent = MarketAnalystAgent(llm=mock_llm)
    market_data = MarketDataSnapshot(symbol="BTCUSDC")

    mock_prompt = MagicMock()
    mock_prompt.read_text.return_value = "system prompt"
    with patch("src.agents.market_analyst.time.sleep"):
        with patch.object(type(agent), "prompt_path", new_callable=PropertyMock, return_value=mock_prompt):
            result = agent.run(MarketAnalystInput(symbol="BTCUSDC", market_data=market_data))

    assert mock_llm.generate_json.call_count == 2
    assert result.market_bias is MarketBias.BULLISH


def test_agent_retries_up_to_4_times_then_raises() -> None:
    """Verifica che l'agente esegua esattamente 4 tentativi prima di propagare l'eccezione."""
    mock_llm = MagicMock()
    mock_llm.generate_json.side_effect = RuntimeError("Risposta non valida")

    agent = MarketAnalystAgent(llm=mock_llm)
    market_data = MarketDataSnapshot(symbol="BTCUSDC")

    mock_prompt = MagicMock()
    mock_prompt.read_text.return_value = "system prompt"
    with patch("src.agents.market_analyst.time.sleep"):
        with patch.object(type(agent), "prompt_path", new_callable=PropertyMock, return_value=mock_prompt):
            with pytest.raises(RuntimeError):
                agent.run(MarketAnalystInput(symbol="BTCUSDC", market_data=market_data))

    assert mock_llm.generate_json.call_count == 4


def test_agent_retry_backoff_sleep_values() -> None:
    """Verifica che il backoff tra i retry segua la progressione 4s, 8s, 16s."""
    mock_llm = MagicMock()
    mock_llm.generate_json.side_effect = RuntimeError("Risposta non valida")

    agent = MarketAnalystAgent(llm=mock_llm)
    market_data = MarketDataSnapshot(symbol="BTCUSDC")

    mock_prompt = MagicMock()
    mock_prompt.read_text.return_value = "system prompt"
    with patch("src.agents.market_analyst.time.sleep") as mock_sleep:
        with patch.object(type(agent), "prompt_path", new_callable=PropertyMock, return_value=mock_prompt):
            with pytest.raises(RuntimeError):
                agent.run(MarketAnalystInput(symbol="BTCUSDC", market_data=market_data))

    sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
    assert sleep_calls == [4, 8, 16]


def test_agent_warning_includes_raw_response() -> None:
    """Verifica che il WARNING del retry includa la risposta raw del LLM."""
    mock_llm = MagicMock()
    valid_response = {
        "market_bias": "BULLISH",
        "signal_strength": 0.8,
        "confidence": 0.75,
        "summary": "Segnale rialzista.",
    }
    mock_llm.generate_json.side_effect = [
        RuntimeError("Risposta non valida"),
        valid_response,
    ]

    agent = MarketAnalystAgent(llm=mock_llm)
    market_data = MarketDataSnapshot(symbol="BTCUSDC")

    mock_prompt = MagicMock()
    mock_prompt.read_text.return_value = "system prompt"
    with patch("src.agents.market_analyst.time.sleep"):
        with patch.object(type(agent), "prompt_path", new_callable=PropertyMock, return_value=mock_prompt):
            with patch.object(agent, "_logger") as mock_logger:
                agent.run(MarketAnalystInput(symbol="BTCUSDC", market_data=market_data))

    mock_logger.warning.assert_called_once()
    warning_args = mock_logger.warning.call_args.args
    assert "Risposta:" in warning_args[0]
