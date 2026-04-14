"""Test unitari per TelegramNotifier."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.utils.telegram_notifier import TelegramNotifier, escape_html


# ---------- send_message — caso nominale ----------


@patch("src.utils.telegram_notifier.requests.post")
def test_send_message_calls_post_with_correct_url(mock_post: MagicMock) -> None:
    """send_message deve chiamare POST sull'URL corretto."""
    mock_post.return_value.raise_for_status = MagicMock()
    notifier = TelegramNotifier(bot_token="TOKEN123", chat_id="CHAT456")

    notifier.send_message("Ciao")

    expected_url = "https://api.telegram.org/botTOKEN123/sendMessage"
    mock_post.assert_called_once()
    actual_url = mock_post.call_args.args[0]
    assert actual_url == expected_url


@patch("src.utils.telegram_notifier.requests.post")
def test_send_message_sends_correct_payload(mock_post: MagicMock) -> None:
    """send_message deve includere chat_id, text e parse_mode nel payload."""
    mock_post.return_value.raise_for_status = MagicMock()
    notifier = TelegramNotifier(bot_token="TOKEN123", chat_id="CHAT456")

    notifier.send_message("Test messaggio")

    payload = mock_post.call_args.kwargs["json"]
    assert payload["chat_id"] == "CHAT456"
    assert payload["text"] == "Test messaggio"
    assert payload["parse_mode"] == "HTML"


# ---------- send_message — errori di rete ----------


@patch("src.utils.telegram_notifier.requests.post")
def test_send_message_does_not_raise_on_network_error(mock_post: MagicMock) -> None:
    """Gli errori di connessione non devono propagare eccezioni."""
    mock_post.side_effect = ConnectionError("timeout")
    notifier = TelegramNotifier(bot_token="TOKEN123", chat_id="CHAT456")

    notifier.send_message("Ciao")  # non deve sollevare


@patch("src.utils.telegram_notifier.requests.post")
def test_send_message_does_not_raise_on_http_error(mock_post: MagicMock) -> None:
    """Gli errori HTTP (raise_for_status) non devono propagare eccezioni."""
    from requests import HTTPError

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = HTTPError("401 Unauthorized")
    mock_post.return_value = mock_response
    notifier = TelegramNotifier(bot_token="TOKEN_INVALIDO", chat_id="CHAT456")

    notifier.send_message("Ciao")  # non deve sollevare


# ---------- notifier disabilitato ----------


@patch("src.utils.telegram_notifier.requests.post")
def test_send_message_skips_if_token_missing(mock_post: MagicMock) -> None:
    """Se bot_token è None, send_message non chiama requests.post."""
    notifier = TelegramNotifier(bot_token=None, chat_id="CHAT456")

    notifier.send_message("Ciao")

    mock_post.assert_not_called()


@patch("src.utils.telegram_notifier.requests.post")
def test_send_message_skips_if_chat_id_missing(mock_post: MagicMock) -> None:
    """Se chat_id è None, send_message non chiama requests.post."""
    notifier = TelegramNotifier(bot_token="TOKEN123", chat_id=None)

    notifier.send_message("Ciao")

    mock_post.assert_not_called()


@patch("src.utils.telegram_notifier.requests.post")
def test_send_message_skips_if_both_missing(mock_post: MagicMock) -> None:
    """Se entrambi sono None, send_message non chiama requests.post."""
    notifier = TelegramNotifier(bot_token=None, chat_id=None)

    notifier.send_message("Ciao")

    mock_post.assert_not_called()


# ---------- escape_html ----------


def test_escape_html_escapes_special_characters() -> None:
    """escape_html deve convertire <, > e & nei rispettivi escape HTML."""
    assert escape_html("<script>alert('xss')</script>") == "&lt;script&gt;alert('xss')&lt;/script&gt;"
    assert escape_html("a & b") == "a &amp; b"
    assert escape_html("no special chars") == "no special chars"
