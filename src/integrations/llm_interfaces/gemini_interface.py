from __future__ import annotations

import json
import logging
from typing import Any, ClassVar, Mapping

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

from src.integrations.llm_interfaces.base_llm_interface import BaseLlmInterface

_logger = logging.getLogger("mdk_crypto_trading.gemini_interface")


class GeminiInterface(BaseLlmInterface):
    """Implementazione di BaseLlmInterface per il provider Google Gemini."""

    _PROVIDER_NAME: ClassVar[str] = "Gemini"
    _RETRYABLE_ERRORS: ClassVar[tuple[type[BaseException], ...]] = (
        genai_errors.ServerError,
    )
    _NON_RETRYABLE_PROVIDER_ERROR: ClassVar[type[BaseException]] = genai_errors.ClientError

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._client = genai.Client(api_key=api_key)

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def _logger(self) -> logging.Logger:
        return _logger

    def _config_kwargs(self, system_prompt: str) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "system_instruction": system_prompt,
            "response_mime_type": "application/json",
            "max_output_tokens": self._max_tokens,
        }
        if self._temperature is not None:
            kwargs["temperature"] = self._temperature
        return kwargs

    def _call_provider(
        self,
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> Any:
        return self._client.models.generate_content(
            model=self._model,
            contents=json.dumps(dict(user_payload)),
            config=genai_types.GenerateContentConfig(
                **self._config_kwargs(system_prompt)
            ),
        )

    def _extract_text(self, response: Any) -> str:
        return response.text or ""

    def _log_empty_response(self, response: Any) -> None:
        finish_reason = (
            response.candidates[0].finish_reason
            if response.candidates
            else None
        )
        self._logger.warning(
            "Gemini risposta vuota | finish_reason: %s | usage_metadata: %s",
            finish_reason,
            response.usage_metadata,
        )
