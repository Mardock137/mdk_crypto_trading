from __future__ import annotations

import json
import logging
from typing import Any, Mapping

from anthropic import (
    Anthropic,
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.integrations.llm_interfaces.base_llm_interface import BaseLlmInterface

_logger = logging.getLogger("mdk_crypto_trading.anthropic_interface")

# Eccezioni temporanee su cui fare retry automatico
_RETRYABLE_ERRORS = (RateLimitError, APIConnectionError, APITimeoutError)


class AnthropicInterface(BaseLlmInterface):
    """Implementazione di BaseLlmInterface per il provider Anthropic (Claude)."""

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> None:
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens or 1024
        self._client = Anthropic(api_key=api_key)

    @property
    def model_name(self) -> str:
        return self._model

    @retry(
        retry=retry_if_exception_type(_RETRYABLE_ERRORS),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text if response.content else ""
        except _RETRYABLE_ERRORS:
            raise
        except APIStatusError as exc:
            raise RuntimeError(f"Errore API Anthropic: {exc}") from exc

    @retry(
        retry=retry_if_exception_type(_RETRYABLE_ERRORS),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def generate_json(
        self,
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": json.dumps(dict(user_payload))}
                ],
            )
            raw = response.content[0].text if response.content else ""
            if not raw or not raw.strip():
                raise RuntimeError("Risposta vuota dal provider Anthropic.")
            result: dict[str, Any] = json.loads(raw)
            if not result:
                raise RuntimeError("Il provider Anthropic ha risposto con un JSON vuoto.")
            return result
        except _RETRYABLE_ERRORS:
            raise
        except APIStatusError as exc:
            raise RuntimeError(f"Errore API Anthropic: {exc}") from exc
        except json.JSONDecodeError as exc:
            _logger.warning("Risposta raw non decodificabile di Anthropic: %r", raw)
            raise RuntimeError(
                f"Impossibile decodificare la risposta JSON di Anthropic: {exc}"
            ) from exc
