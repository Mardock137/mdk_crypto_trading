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
def test_generate_json_empty_text_returns_empty_dict(mock_anthropic_cls: MagicMock) -> None:
    """Verifica che generate_json restituisca {} quando Claude risponde con stringa vuota."""
    mock_client = mock_anthropic_cls.return_value
    mock_content_block = MagicMock()
    mock_content_block.text = ""
    mock_response = MagicMock()
    mock_response.content = [mock_content_block]
    mock_client.messages.create.return_value = mock_response

    interface = AnthropicInterface(api_key="fake-key", model="claude-sonnet-4-6")
    result = interface.generate_json("system prompt", {"chiave": "valore"})

    assert result == {}


@patch("src.integrations.llm_interfaces.anthropic_interface.Anthropic")
def test_generate_json_no_content_returns_empty_dict(mock_anthropic_cls: MagicMock) -> None:
    """Verifica che generate_json restituisca {} quando Claude risponde senza content."""
    mock_client = mock_anthropic_cls.return_value
    mock_response = MagicMock()
    mock_response.content = []
    mock_client.messages.create.return_value = mock_response

    interface = AnthropicInterface(api_key="fake-key", model="claude-sonnet-4-6")
    result = interface.generate_json("system prompt", {"chiave": "valore"})

    assert result == {}


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
