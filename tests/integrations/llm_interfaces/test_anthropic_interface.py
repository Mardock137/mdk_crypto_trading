from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from src.integrations.llm_interfaces.anthropic_interface import AnthropicInterface


@patch("src.integrations.llm_interfaces.anthropic_interface.Anthropic")
def test_model_name_returns_configured_value(mock_anthropic_cls: MagicMock) -> None:
    """Verifica che model_name restituisca il valore passato al costruttore."""
    interface = AnthropicInterface(api_key="fake-key", model="claude-sonnet-4-6")
    assert interface.model_name == "claude-sonnet-4-6"


@patch("src.integrations.llm_interfaces.anthropic_interface.Anthropic")
def test_generate_text_calls_messages_create(mock_anthropic_cls: MagicMock) -> None:
    """Verifica che generate_text chiami messages.create con i parametri corretti."""
    mock_client = mock_anthropic_cls.return_value
    mock_content_block = MagicMock()
    mock_content_block.text = "Risposta di test"
    mock_response = MagicMock()
    mock_response.content = [mock_content_block]
    mock_client.messages.create.return_value = mock_response

    interface = AnthropicInterface(api_key="fake-key", model="claude-sonnet-4-6")
    result = interface.generate_text("system prompt", "user prompt")

    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["system"] == "system prompt"
    assert call_kwargs["messages"] == [{"role": "user", "content": "user prompt"}]
    assert call_kwargs["temperature"] == 0.7
    assert result == "Risposta di test"


@patch("src.integrations.llm_interfaces.anthropic_interface.Anthropic")
def test_generate_json_calls_messages_create_and_parses_response(mock_anthropic_cls: MagicMock) -> None:
    """Verifica che generate_json chiami messages.create e parsi correttamente il JSON."""
    mock_client = mock_anthropic_cls.return_value
    mock_content_block = MagicMock()
    mock_content_block.text = '{"risultato": "ok"}'
    mock_response = MagicMock()
    mock_response.content = [mock_content_block]
    mock_client.messages.create.return_value = mock_response

    interface = AnthropicInterface(api_key="fake-key", model="claude-sonnet-4-6")
    result = interface.generate_json("system prompt", {"chiave": "valore"})

    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["system"] == "system prompt"
    assert "output_config" not in call_kwargs
    assert result == {"risultato": "ok"}


@patch("src.integrations.llm_interfaces.anthropic_interface.Anthropic")
def test_generate_json_empty_text_raises(mock_anthropic_cls: MagicMock) -> None:
    """Verifica che generate_json sollevi RuntimeError quando Claude risponde con stringa vuota."""
    mock_client = mock_anthropic_cls.return_value
    mock_content_block = MagicMock()
    mock_content_block.text = ""
    mock_response = MagicMock()
    mock_response.content = [mock_content_block]
    mock_client.messages.create.return_value = mock_response

    interface = AnthropicInterface(api_key="fake-key", model="claude-sonnet-4-6")

    with pytest.raises(RuntimeError, match="Risposta vuota"):
        interface.generate_json("system prompt", {"chiave": "valore"})


@patch("src.integrations.llm_interfaces.anthropic_interface.Anthropic")
def test_generate_json_no_content_raises(mock_anthropic_cls: MagicMock) -> None:
    """Verifica che generate_json sollevi RuntimeError quando Claude risponde senza content."""
    mock_client = mock_anthropic_cls.return_value
    mock_response = MagicMock()
    mock_response.content = []
    mock_client.messages.create.return_value = mock_response

    interface = AnthropicInterface(api_key="fake-key", model="claude-sonnet-4-6")

    with pytest.raises(RuntimeError, match="Risposta vuota"):
        interface.generate_json("system prompt", {"chiave": "valore"})


@patch("src.integrations.llm_interfaces.anthropic_interface.Anthropic")
def test_generate_json_empty_dict_response_raises(mock_anthropic_cls: MagicMock) -> None:
    """Verifica che generate_json sollevi RuntimeError quando Claude risponde con JSON vuoto {}."""
    mock_client = mock_anthropic_cls.return_value
    mock_content_block = MagicMock()
    mock_content_block.text = "{}"
    mock_response = MagicMock()
    mock_response.content = [mock_content_block]
    mock_client.messages.create.return_value = mock_response

    interface = AnthropicInterface(api_key="fake-key", model="claude-sonnet-4-6")

    with pytest.raises(RuntimeError, match="JSON vuoto"):
        interface.generate_json("system prompt", {"chiave": "valore"})


@patch("src.integrations.llm_interfaces.anthropic_interface._logger")
@patch("src.integrations.llm_interfaces.anthropic_interface.Anthropic")
def test_generate_json_invalid_json_logs_raw_and_raises(
    mock_anthropic_cls: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Verifica che generate_json loggi la risposta raw e rilanci RuntimeError su JSON non valido."""
    mock_client = mock_anthropic_cls.return_value
    mock_content_block = MagicMock()
    mock_content_block.text = "questo non e json"
    mock_response = MagicMock()
    mock_response.content = [mock_content_block]
    mock_client.messages.create.return_value = mock_response

    interface = AnthropicInterface(api_key="fake-key", model="claude-sonnet-4-6")

    with pytest.raises(RuntimeError, match="Impossibile decodificare"):
        interface.generate_json("system prompt", {"chiave": "valore"})

    mock_logger.warning.assert_called_once()
    assert "questo non e json" in mock_logger.warning.call_args.args[1]


@patch("src.integrations.llm_interfaces.anthropic_interface._logger")
@patch("src.integrations.llm_interfaces.anthropic_interface.Anthropic")
def test_generate_json_empty_response_logs_stop_reason(
    mock_anthropic_cls: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Verifica che generate_json loggi stop_reason e usage quando Anthropic risponde con stringa vuota."""
    mock_client = mock_anthropic_cls.return_value
    mock_content_block = MagicMock()
    mock_content_block.text = ""
    mock_response = MagicMock()
    mock_response.content = [mock_content_block]
    mock_response.stop_reason = "max_tokens"
    mock_response.usage = MagicMock(input_tokens=200, output_tokens=0)
    mock_client.messages.create.return_value = mock_response

    interface = AnthropicInterface(api_key="fake-key", model="claude-sonnet-4-6")

    with pytest.raises(RuntimeError, match="Risposta vuota"):
        interface.generate_json("system prompt", {"chiave": "valore"})

    mock_logger.warning.assert_called_once()
    warning_args = mock_logger.warning.call_args.args
    assert "stop_reason" in warning_args[0]
    assert "max_tokens" in warning_args


@patch("src.integrations.llm_interfaces.anthropic_interface.Anthropic")
def test_custom_temperature_and_max_tokens_are_forwarded(mock_anthropic_cls: MagicMock) -> None:
    """Verifica che temperature e max_tokens personalizzati vengano passati all'API."""
    mock_client = mock_anthropic_cls.return_value
    mock_content_block = MagicMock()
    mock_content_block.text = "ok"
    mock_response = MagicMock()
    mock_response.content = [mock_content_block]
    mock_client.messages.create.return_value = mock_response

    interface = AnthropicInterface(
        api_key="fake-key",
        model="claude-sonnet-4-6",
        temperature=0.2,
        max_tokens=512,
    )
    interface.generate_text("s", "u")

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["temperature"] == 0.2
    assert call_kwargs["max_tokens"] == 512


# --- Test per _strip_markdown_json ---

from src.integrations.llm_interfaces.anthropic_interface import _strip_markdown_json


def test_strip_markdown_json_with_json_tag() -> None:
    """Verifica che il wrapping ```json...``` venga rimosso correttamente."""
    raw = '```json\n{"market_bias": "BULLISH", "confidence": 0.7}\n```'
    result = _strip_markdown_json(raw)
    assert result == '{"market_bias": "BULLISH", "confidence": 0.7}'


def test_strip_markdown_json_without_tag() -> None:
    """Verifica che il wrapping ```...``` (senza 'json') venga rimosso correttamente."""
    raw = '```\n{"market_bias": "BEARISH"}\n```'
    result = _strip_markdown_json(raw)
    assert result == '{"market_bias": "BEARISH"}'


def test_strip_markdown_json_with_extra_text_before() -> None:
    """Verifica che il testo prima del JSON venga ignorato (fallback su primo '{')."""
    raw = 'Here is my analysis:\n{"market_bias": "NEUTRAL", "confidence": 0.5}'
    result = _strip_markdown_json(raw)
    assert result == '{"market_bias": "NEUTRAL", "confidence": 0.5}'


def test_strip_markdown_json_pure_json_unchanged() -> None:
    """Verifica che un JSON puro passi invariato (non-regressione)."""
    raw = '{"market_bias": "BULLISH", "signal_strength": 0.8}'
    result = _strip_markdown_json(raw)
    assert result == raw


@patch("src.integrations.llm_interfaces.anthropic_interface.Anthropic")
def test_generate_json_parses_markdown_wrapped_response(mock_anthropic_cls: MagicMock) -> None:
    """Verifica che generate_json parsi correttamente una risposta wrappata in ```json...```."""
    mock_client = mock_anthropic_cls.return_value
    mock_content_block = MagicMock()
    mock_content_block.text = '```json\n{"risultato": "ok"}\n```'
    mock_response = MagicMock()
    mock_response.content = [mock_content_block]
    mock_client.messages.create.return_value = mock_response

    interface = AnthropicInterface(api_key="fake-key", model="claude-sonnet-4-6")
    result = interface.generate_json("system prompt", {"chiave": "valore"})

    assert result == {"risultato": "ok"}


@patch("src.integrations.llm_interfaces.anthropic_interface.Anthropic")
def test_generate_json_parses_markdown_wrapped_response_no_tag(mock_anthropic_cls: MagicMock) -> None:
    """Verifica che generate_json parsi correttamente una risposta wrappata in ```...``` (senza tag json)."""
    mock_client = mock_anthropic_cls.return_value
    mock_content_block = MagicMock()
    mock_content_block.text = '```\n{"risultato": "ok"}\n```'
    mock_response = MagicMock()
    mock_response.content = [mock_content_block]
    mock_client.messages.create.return_value = mock_response

    interface = AnthropicInterface(api_key="fake-key", model="claude-sonnet-4-6")
    result = interface.generate_json("system prompt", {"chiave": "valore"})

    assert result == {"risultato": "ok"}


@patch("src.integrations.llm_interfaces.anthropic_interface.Anthropic")
def test_generate_json_parses_response_with_text_prefix(mock_anthropic_cls: MagicMock) -> None:
    """Verifica che generate_json parsi correttamente una risposta con testo prima del JSON."""
    mock_client = mock_anthropic_cls.return_value
    mock_content_block = MagicMock()
    mock_content_block.text = 'Here is the analysis:\n{"risultato": "ok"}'
    mock_response = MagicMock()
    mock_response.content = [mock_content_block]
    mock_client.messages.create.return_value = mock_response

    interface = AnthropicInterface(api_key="fake-key", model="claude-sonnet-4-6")
    result = interface.generate_json("system prompt", {"chiave": "valore"})

    assert result == {"risultato": "ok"}


# --- Test retry su errori server temporanei ---

from anthropic import InternalServerError


@patch("src.integrations.llm_interfaces.anthropic_interface.Anthropic")
def test_generate_json_retries_on_internal_server_error(mock_anthropic_cls: MagicMock) -> None:
    """Verifica che generate_json riprovi automaticamente su InternalServerError (500/529)."""
    mock_client = mock_anthropic_cls.return_value
    mock_content_block = MagicMock()
    mock_content_block.text = '{"risultato": "ok"}'
    mock_success = MagicMock()
    mock_success.content = [mock_content_block]

    error = InternalServerError(
        message="Internal server error",
        response=MagicMock(status_code=500, headers={}),
        body={"type": "error", "error": {"type": "api_error", "message": "Internal server error"}},
    )
    mock_client.messages.create.side_effect = [error, mock_success]

    interface = AnthropicInterface(api_key="fake-key", model="claude-sonnet-4-6")
    result = interface.generate_json("system prompt", {"chiave": "valore"})

    assert result == {"risultato": "ok"}
    assert mock_client.messages.create.call_count == 2
