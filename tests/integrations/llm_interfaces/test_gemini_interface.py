from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from src.integrations.llm_interfaces.gemini_interface import GeminiInterface


@patch("src.integrations.llm_interfaces.gemini_interface.genai")
def test_model_name_returns_configured_value(mock_genai: MagicMock) -> None:
    """Verifica che model_name restituisca il valore passato al costruttore."""
    interface = GeminiInterface(api_key="fake-key", model="gemini-2.0-flash")
    assert interface.model_name == "gemini-2.0-flash"


@patch("src.integrations.llm_interfaces.gemini_interface.genai")
def test_generate_text_calls_generate_content(mock_genai: MagicMock) -> None:
    """Verifica che generate_text chiami models.generate_content correttamente."""
    mock_client = mock_genai.Client.return_value
    mock_response = MagicMock()
    mock_response.text = "Risposta di test"
    mock_client.models.generate_content.return_value = mock_response

    interface = GeminiInterface(api_key="fake-key", model="gemini-2.0-flash")
    result = interface.generate_text("system prompt", "user prompt")

    mock_client.models.generate_content.assert_called_once()
    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-2.0-flash"
    assert call_kwargs["contents"] == "user prompt"
    assert result == "Risposta di test"


@patch("src.integrations.llm_interfaces.gemini_interface.genai")
def test_generate_json_uses_json_mime_type(mock_genai: MagicMock) -> None:
    """Verifica che generate_json chiami l'API con response_mime_type JSON."""
    mock_client = mock_genai.Client.return_value
    mock_response = MagicMock()
    mock_response.text = '{"risultato": "ok"}'
    mock_client.models.generate_content.return_value = mock_response

    interface = GeminiInterface(api_key="fake-key", model="gemini-2.0-flash")
    result = interface.generate_json("system prompt", {"chiave": "valore"})

    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    config = call_kwargs["config"]
    assert config.response_mime_type == "application/json"
    assert config.temperature == 0.7
    assert config.max_output_tokens is None
    assert result == {"risultato": "ok"}


@patch("src.integrations.llm_interfaces.gemini_interface._logger")
@patch("src.integrations.llm_interfaces.gemini_interface.genai")
def test_generate_json_invalid_json_logs_raw_and_raises(
    mock_genai: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Verifica che generate_json loggi la risposta raw e rilanci RuntimeError su JSON non valido."""
    mock_client = mock_genai.Client.return_value
    mock_response = MagicMock()
    mock_response.text = "questo non e json"
    mock_client.models.generate_content.return_value = mock_response

    interface = GeminiInterface(api_key="fake-key", model="gemini-2.0-flash")

    with pytest.raises(RuntimeError, match="Impossibile decodificare"):
        interface.generate_json("system prompt", {"chiave": "valore"})

    mock_logger.warning.assert_called_once()
    assert "questo non e json" in mock_logger.warning.call_args.args[1]


@patch("src.integrations.llm_interfaces.gemini_interface.genai")
def test_generate_json_empty_response_raises(mock_genai: MagicMock) -> None:
    """Verifica che generate_json sollevi RuntimeError quando Gemini risponde con testo vuoto."""
    mock_client = mock_genai.Client.return_value
    mock_response = MagicMock()
    mock_response.text = ""
    mock_client.models.generate_content.return_value = mock_response

    interface = GeminiInterface(api_key="fake-key", model="gemini-2.0-flash")

    with pytest.raises(RuntimeError, match="Risposta vuota"):
        interface.generate_json("system prompt", {"chiave": "valore"})


@patch("src.integrations.llm_interfaces.gemini_interface.genai")
def test_generate_json_empty_dict_response_raises(mock_genai: MagicMock) -> None:
    """Verifica che generate_json sollevi RuntimeError quando Gemini risponde con JSON vuoto {}."""
    mock_client = mock_genai.Client.return_value
    mock_response = MagicMock()
    mock_response.text = "{}"
    mock_client.models.generate_content.return_value = mock_response

    interface = GeminiInterface(api_key="fake-key", model="gemini-2.0-flash")

    with pytest.raises(RuntimeError, match="JSON vuoto"):
        interface.generate_json("system prompt", {"chiave": "valore"})


@patch("src.integrations.llm_interfaces.gemini_interface._logger")
@patch("src.integrations.llm_interfaces.gemini_interface.genai")
def test_generate_json_empty_response_logs_finish_reason(
    mock_genai: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Verifica che generate_json loggi finish_reason e usage_metadata quando Gemini risponde con testo vuoto."""
    mock_client = mock_genai.Client.return_value
    mock_candidate = MagicMock()
    mock_candidate.finish_reason = "SAFETY"
    mock_response = MagicMock()
    mock_response.text = ""
    mock_response.candidates = [mock_candidate]
    mock_response.usage_metadata = MagicMock(prompt_token_count=150, candidates_token_count=0)
    mock_client.models.generate_content.return_value = mock_response

    interface = GeminiInterface(api_key="fake-key", model="gemini-2.0-flash")

    with pytest.raises(RuntimeError, match="Risposta vuota"):
        interface.generate_json("system prompt", {"chiave": "valore"})

    mock_logger.warning.assert_called_once()
    warning_args = mock_logger.warning.call_args.args
    assert "finish_reason" in warning_args[0]
    assert "SAFETY" in warning_args


@patch("src.integrations.llm_interfaces.gemini_interface.genai")
def test_custom_temperature_and_max_tokens_are_forwarded(mock_genai: MagicMock) -> None:
    """Verifica che temperature e max_tokens personalizzati vengano passati al config."""
    mock_client = mock_genai.Client.return_value
    mock_response = MagicMock()
    mock_response.text = "ok"
    mock_client.models.generate_content.return_value = mock_response

    interface = GeminiInterface(api_key="fake-key", model="gemini-2.0-flash", temperature=0.2, max_tokens=512)
    interface.generate_text("s", "u")

    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    config = call_kwargs["config"]
    assert config.temperature == 0.2
    assert config.max_output_tokens == 512
