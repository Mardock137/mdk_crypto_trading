from __future__ import annotations

import json
import logging
from typing import Any, Mapping

from openai import (
    OpenAI,
    APIError,
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.integrations.llm_interfaces.base_llm_interface import BaseLlmInterface

_logger = logging.getLogger("mdk_crypto_trading.openai_interface")

# Eccezioni temporanee su cui fare retry automatico
_RETRYABLE_ERRORS = (
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
)


class OpenAiInterface(BaseLlmInterface):
    """Implementazione di BaseLlmInterface per il provider OpenAI."""

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._reasoning_effort = reasoning_effort
        self._client = OpenAI(api_key=api_key)

    @property
    def model_name(self) -> str:
        return self._model

    def _build_kwargs(self) -> dict[str, Any]:
        """Costruisce i kwargs dinamici per chat.completions.create().

        Con reasoning_effort: include reasoning_effort, esclude temperature.
        Senza reasoning_effort: include temperature, esclude reasoning_effort.
        max_completion_tokens è sempre incluso se presente.
        """
        kwargs: dict[str, Any] = {}
        if self._reasoning_effort is not None:
            kwargs["reasoning_effort"] = self._reasoning_effort
        else:
            kwargs["temperature"] = self._temperature
        if self._max_tokens is not None:
            kwargs["max_completion_tokens"] = self._max_tokens
        return kwargs

    @retry(
        retry=retry_if_exception_type(_RETRYABLE_ERRORS),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        try:
            kwargs = self._build_kwargs()
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                **kwargs,
            )
            content = (
                response.choices[0].message.content if response.choices else None
            )
            if not content:
                if response.choices:
                    _logger.warning(
                        "OpenAI generate_text risposta vuota | finish_reason: %s | usage: %s",
                        response.choices[0].finish_reason,
                        response.usage,
                    )
                else:
                    _logger.warning(
                        "OpenAI generate_text risposta vuota | choices: [] | usage: %s",
                        response.usage,
                    )
            return content or ""
        except _RETRYABLE_ERRORS:
            raise
        except APIError as exc:
            raise RuntimeError(f"Errore API OpenAI: {exc}") from exc

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
            kwargs = self._build_kwargs()
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(dict(user_payload))},
                ],
                response_format={"type": "json_object"},
                **kwargs,
            )
            raw = (
                response.choices[0].message.content if response.choices else None
            )
            if not raw or not raw.strip():
                if response.choices:
                    _logger.warning(
                        "OpenAI risposta vuota | finish_reason: %s | usage: %s",
                        response.choices[0].finish_reason,
                        response.usage,
                    )
                else:
                    _logger.warning(
                        "OpenAI risposta vuota | choices: [] | usage: %s",
                        response.usage,
                    )
                raise RuntimeError("Risposta vuota dal provider OpenAI.")
            result: dict[str, Any] = json.loads(raw)
            if not result:
                raise RuntimeError("Il provider OpenAI ha risposto con un JSON vuoto.")
            return result
        except _RETRYABLE_ERRORS:
            raise
        except APIError as exc:
            raise RuntimeError(f"Errore API OpenAI: {exc}") from exc
        except json.JSONDecodeError as exc:
            _logger.warning("Risposta raw non decodificabile di OpenAI: %r", raw)
            raise RuntimeError(
                f"Impossibile decodificare la risposta JSON di OpenAI: {exc}"
            ) from exc
