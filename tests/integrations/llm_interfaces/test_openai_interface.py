from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from src.integrations.llm_interfaces.openai_interface import OpenAiInterface


@patch("src.integrations.llm_interfaces.openai_interface.OpenAI")
def test_model_name_returns_configured_value(mock_openai_cls: MagicMock) -> None:
    """Verifica che model_name restituisca il valore passato al costruttore."""
    interface = OpenAiInterface(api_key="fake-key", model="gpt-4o")
    assert interface.model_name == "gpt-4o"


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
    mock_choice.message.content = '{"ok": true}'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    interface = OpenAiInterface(api_key="fake-key", model="gpt-4o", temperature=0.2, max_tokens=512)
    interface.generate_json("s", {"k": "v"})

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["temperature"] == 0.2
    assert call_kwargs["max_completion_tokens"] == 512
    assert "reasoning_effort" not in call_kwargs


@patch("src.integrations.llm_interfaces.openai_interface.OpenAI")
def test_reasoning_effort_is_forwarded_when_set(mock_openai_cls: MagicMock) -> None:
    """Verifica che reasoning_effort venga passato all'API quando configurato."""
    mock_client = mock_openai_cls.return_value
    mock_choice = MagicMock()
    mock_choice.message.content = '{"ok": true}'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    interface = OpenAiInterface(
        api_key="fake-key", model="gpt-5.4", reasoning_effort="high",
    )
    interface.generate_json("s", {"k": "v"})

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["reasoning_effort"] == "high"
    assert "temperature" not in call_kwargs


@patch("src.integrations.llm_interfaces.openai_interface._logger")
@patch("src.integrations.llm_interfaces.openai_interface.OpenAI")
def test_generate_json_invalid_json_logs_raw_and_raises(
    mock_openai_cls: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Verifica che generate_json loggi la risposta raw e rilanci RuntimeError su JSON non valido."""
    mock_client = mock_openai_cls.return_value
    mock_choice = MagicMock()
    mock_choice.message.content = "questo non e json"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    interface = OpenAiInterface(api_key="fake-key", model="gpt-4o")

    with pytest.raises(RuntimeError, match="Impossibile decodificare"):
        interface.generate_json("system prompt", {"chiave": "valore"})

    mock_logger.warning.assert_called_once()
    assert "questo non e json" in mock_logger.warning.call_args.args[1]


@patch("src.integrations.llm_interfaces.openai_interface.OpenAI")
def test_generate_json_empty_response_raises(mock_openai_cls: MagicMock) -> None:
    """Verifica che generate_json sollevi RuntimeError quando OpenAI risponde con stringa vuota."""
    mock_client = mock_openai_cls.return_value
    mock_choice = MagicMock()
    mock_choice.message.content = ""
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    interface = OpenAiInterface(api_key="fake-key", model="gpt-4o")

    with pytest.raises(RuntimeError, match="Risposta vuota"):
        interface.generate_json("system prompt", {"chiave": "valore"})


@patch("src.integrations.llm_interfaces.openai_interface.OpenAI")
def test_generate_json_empty_dict_response_raises(mock_openai_cls: MagicMock) -> None:
    """Verifica che generate_json sollevi RuntimeError quando OpenAI risponde con JSON vuoto {}."""
    mock_client = mock_openai_cls.return_value
    mock_choice = MagicMock()
    mock_choice.message.content = "{}"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    interface = OpenAiInterface(api_key="fake-key", model="gpt-4o")

    with pytest.raises(RuntimeError, match="JSON vuoto"):
        interface.generate_json("system prompt", {"chiave": "valore"})


@patch("src.integrations.llm_interfaces.openai_interface._logger")
@patch("src.integrations.llm_interfaces.openai_interface.OpenAI")
def test_generate_json_empty_response_logs_finish_reason(
    mock_openai_cls: MagicMock,
    mock_logger: MagicMock,
) -> None:
    """Verifica che generate_json loggi finish_reason e usage quando OpenAI risponde con stringa vuota."""
    mock_client = mock_openai_cls.return_value
    mock_choice = MagicMock()
    mock_choice.message.content = ""
    mock_choice.finish_reason = "content_filter"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=0)
    mock_client.chat.completions.create.return_value = mock_response

    interface = OpenAiInterface(api_key="fake-key", model="gpt-4o")

    with pytest.raises(RuntimeError, match="Risposta vuota"):
        interface.generate_json("system prompt", {"chiave": "valore"})

    mock_logger.warning.assert_called_once()
    warning_args = mock_logger.warning.call_args.args
    assert "finish_reason" in warning_args[0]
    assert "content_filter" in warning_args


@patch("src.integrations.llm_interfaces.openai_interface.OpenAI")
def test_reasoning_effort_absent_when_none(mock_openai_cls: MagicMock) -> None:
    """Verifica che reasoning_effort non venga passato all'API se non configurato."""
    mock_client = mock_openai_cls.return_value
    mock_choice = MagicMock()
    mock_choice.message.content = '{"ok": true}'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    interface = OpenAiInterface(api_key="fake-key", model="gpt-4o")
    interface.generate_json("s", {"k": "v"})

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert "reasoning_effort" not in call_kwargs


# --- Test retry su errori server temporanei ---

from openai import InternalServerError as OpenAIInternalServerError


@patch("src.integrations.llm_interfaces.openai_interface.OpenAI")
def test_generate_json_retries_on_internal_server_error(mock_openai_cls: MagicMock) -> None:
    """Verifica che generate_json riprovi automaticamente su InternalServerError (500)."""
    mock_client = mock_openai_cls.return_value
    mock_choice = MagicMock()
    mock_choice.message.content = '{"risultato": "ok"}'
    mock_success = MagicMock()
    mock_success.choices = [mock_choice]

    error = OpenAIInternalServerError(
        message="Internal server error",
        response=MagicMock(status_code=500, headers={}),
        body={"error": {"message": "Internal server error", "type": "server_error"}},
    )
    mock_client.chat.completions.create.side_effect = [error, mock_success]

    interface = OpenAiInterface(api_key="fake-key", model="gpt-4o")
    result = interface.generate_json("system prompt", {"chiave": "valore"})

    assert result == {"risultato": "ok"}
    assert mock_client.chat.completions.create.call_count == 2
