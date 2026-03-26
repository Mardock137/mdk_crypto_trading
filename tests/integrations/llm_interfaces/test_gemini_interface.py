from __future__ import annotations

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
