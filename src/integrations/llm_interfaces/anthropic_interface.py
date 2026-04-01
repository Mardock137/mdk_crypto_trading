from __future__ import annotations

import json
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
            raw = response.content[0].text if response.content else "{}"
            result: dict[str, Any] = json.loads(raw)
            return result
        except _RETRYABLE_ERRORS:
            raise
        except APIStatusError as exc:
            raise RuntimeError(f"Errore API Anthropic: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Impossibile decodificare la risposta JSON di Anthropic: {exc}"
            ) from exc
