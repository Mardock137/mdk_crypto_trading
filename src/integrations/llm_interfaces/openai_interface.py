from __future__ import annotations

import json
from typing import Any, Mapping

from openai import (
    OpenAI,
    APIError,
    APIConnectionError,
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


class OpenAiInterface(BaseLlmInterface):
    """Implementazione di BaseLlmInterface per il provider OpenAI."""

    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
        self._client = OpenAI(api_key=api_key)

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
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = (
                response.choices[0].message.content if response.choices else None
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
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(dict(user_payload))},
                ],
                response_format={"type": "json_object"},
            )
            raw = (
                response.choices[0].message.content if response.choices else None
            )
            result: dict[str, Any] = json.loads(raw or "{}")
            return result
        except _RETRYABLE_ERRORS:
            raise
        except APIError as exc:
            raise RuntimeError(f"Errore API OpenAI: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Impossibile decodificare la risposta JSON di OpenAI: {exc}"
            ) from exc
