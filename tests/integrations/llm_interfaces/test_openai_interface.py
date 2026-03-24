from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.integrations.llm_interfaces.openai_interface import OpenAiInterface


@patch("src.integrations.llm_interfaces.openai_interface.OpenAI")
def test_model_name_returns_configured_value(mock_openai_cls: MagicMock) -> None:
    """Verifica che model_name restituisca il valore passato al costruttore."""
    interface = OpenAiInterface(api_key="fake-key", model="gpt-4o")
    assert interface.model_name == "gpt-4o"


@patch("src.integrations.llm_interfaces.openai_interface.OpenAI")
def test_generate_text_calls_chat_completions(mock_openai_cls: MagicMock) -> None:
    """Verifica che generate_text chiami chat.completions.create con i messaggi corretti."""
    mock_client = mock_openai_cls.return_value
    mock_choice = MagicMock()
    mock_choice.message.content = "Risposta di test"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    interface = OpenAiInterface(api_key="fake-key", model="gpt-4o")
    result = interface.generate_text("system prompt", "user prompt")

    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o"
    assert call_kwargs["messages"] == [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "user prompt"},
    ]
    assert result == "Risposta di test"


@patch("src.integrations.llm_interfaces.openai_interface.OpenAI")
def test_generate_json_uses_json_response_format(mock_openai_cls: MagicMock) -> None:
    """Verifica che generate_json chiami l'API con response_format json_object."""
    mock_client = mock_openai_cls.return_value
    mock_choice = MagicMock()
    mock_choice.message.content = '{"risultato": "ok"}'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    interface = OpenAiInterface(api_key="fake-key", model="gpt-4o")
    result = interface.generate_json("system prompt", {"chiave": "valore"})

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["response_format"] == {"type": "json_object"}
    assert result == {"risultato": "ok"}
