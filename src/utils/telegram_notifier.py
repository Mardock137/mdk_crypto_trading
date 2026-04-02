from __future__ import annotations

import logging

import requests

_TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
_logger = logging.getLogger("mdk_crypto_trading.telegram_notifier")


class TelegramNotifier:
    """Invia notifiche via Telegram Bot API.

    Se bot_token o chat_id sono assenti (None o stringa vuota), le notifiche
    sono silenziosamente disabilitate. Nessuna eccezione viene mai propagata
    al codice chiamante: gli errori di rete vengono solo loggati.
    """

    def __init__(self, bot_token: str | None, chat_id: str | None) -> None:
        self._bot_token = bot_token or ""
        self._chat_id = chat_id or ""
        self._enabled = bool(self._bot_token and self._chat_id)

    def send_message(self, text: str) -> None:
        """Invia un messaggio al chat Telegram configurato.

        Non solleva mai eccezioni: gli errori vengono loggati e ignorati.
        """
        if not self._enabled:
            return
        try:
            url = _TELEGRAM_API_URL.format(token=self._bot_token)
            response = requests.post(
                url,
                json={
                    "chat_id": self._chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                },
                timeout=10,
            )
            response.raise_for_status()
        except Exception as exc:
            _logger.warning("Telegram: invio fallito: %s", exc)
