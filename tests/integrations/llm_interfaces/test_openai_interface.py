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
    assert call_kwargs["temperature"] == 0.7
    assert "max_completion_tokens" not in call_kwargs
    assert "reasoning_effort" not in call_kwargs
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
    assert call_kwargs["temperature"] == 0.7
    assert "max_completion_tokens" not in call_kwargs
    assert "reasoning_effort" not in call_kwargs
    assert result == {"risultato": "ok"}


@patch("src.integrations.llm_interfaces.openai_interface.OpenAI")
def test_custom_temperature_and_max_tokens_are_forwarded(mock_openai_cls: MagicMock) -> None:
    """Verifica che temperature e max_tokens personalizzati vengano passati all'API."""
    mock_client = mock_openai_cls.return_value
    mock_choice = MagicMock()
    mock_choice.message.content = "ok"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    interface = OpenAiInterface(api_key="fake-key", model="gpt-4o", temperature=0.2, max_tokens=512)
    interface.generate_text("s", "u")

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["temperature"] == 0.2
    assert call_kwargs["max_completion_tokens"] == 512
    assert "reasoning_effort" not in call_kwargs


@patch("src.integrations.llm_interfaces.openai_interface.OpenAI")
def test_reasoning_effort_is_forwarded_when_set(mock_openai_cls: MagicMock) -> None:
    """Verifica che reasoning_effort venga passato all'API quando configurato."""
    mock_client = mock_openai_cls.return_value
    mock_choice = MagicMock()
    mock_choice.message.content = "ok"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    interface = OpenAiInterface(
        api_key="fake-key", model="gpt-5.4", reasoning_effort="high",
    )
    interface.generate_text("s", "u")

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["reasoning_effort"] == "high"
    assert "temperature" not in call_kwargs


@patch("src.integrations.llm_interfaces.openai_interface.OpenAI")
def test_reasoning_effort_absent_when_none(mock_openai_cls: MagicMock) -> None:
    """Verifica che reasoning_effort non venga passato all'API se non configurato."""
    mock_client = mock_openai_cls.return_value
    mock_choice = MagicMock()
    mock_choice.message.content = "ok"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    interface = OpenAiInterface(api_key="fake-key", model="gpt-4o")
    interface.generate_text("s", "u")

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert "reasoning_effort" not in call_kwargs
