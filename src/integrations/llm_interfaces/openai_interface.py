from __future__ import annotations

import json
import logging
from typing import Any, ClassVar, Mapping

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from src.integrations.llm_interfaces.base_llm_interface import BaseLlmInterface

_logger = logging.getLogger("mdk_crypto_trading.openai_interface")


class OpenAiInterface(BaseLlmInterface):
    """Implementazione di BaseLlmInterface per il provider OpenAI."""

    _PROVIDER_NAME: ClassVar[str] = "OpenAI"
    _RETRYABLE_ERRORS: ClassVar[tuple[type[BaseException], ...]] = (
        RateLimitError,
        APIConnectionError,
        APITimeoutError,
        InternalServerError,
    )
    _NON_RETRYABLE_PROVIDER_ERROR: ClassVar[type[BaseException]] = APIError

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

    @property
    def _logger(self) -> logging.Logger:
        return _logger

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

    def _call_provider(
        self,
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> Any:
        return self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(dict(user_payload))},
            ],
            response_format={"type": "json_object"},
            **self._build_kwargs(),
        )

    def _extract_text(self, response: Any) -> str:
        if not response.choices:
            return ""
        content = response.choices[0].message.content
        return content or ""

    def _log_empty_response(self, response: Any) -> None:
        if response.choices:
            self._logger.warning(
                "OpenAI risposta vuota | finish_reason: %s | usage: %s",
                response.choices[0].finish_reason,
                response.usage,
            )
        else:
            self._logger.warning(
                "OpenAI risposta vuota | choices: [] | usage: %s",
                response.usage,
            )
