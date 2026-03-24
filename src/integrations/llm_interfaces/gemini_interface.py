from __future__ import annotations

import json
from typing import Any, Mapping

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.integrations.llm_interfaces.base_llm_interface import BaseLlmInterface


class GeminiInterface(BaseLlmInterface):
    """Implementazione di BaseLlmInterface per il provider Google Gemini."""

    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
        self._client = genai.Client(api_key=api_key)

    @property
    def model_name(self) -> str:
        return self._model

    @retry(
        retry=retry_if_exception_type(genai_errors.ServerError),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_prompt,
                ),
            )
            return response.text or ""
        except genai_errors.ServerError:
            raise
        except genai_errors.ClientError as exc:
            raise RuntimeError(f"Errore API Gemini: {exc}") from exc

    @retry(
        retry=retry_if_exception_type(genai_errors.ServerError),
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
            response = self._client.models.generate_content(
                model=self._model,
                contents=json.dumps(dict(user_payload)),
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                ),
            )
            raw = response.text or "{}"
            result: dict[str, Any] = json.loads(raw)
            return result
        except genai_errors.ServerError:
            raise
        except genai_errors.ClientError as exc:
            raise RuntimeError(f"Errore API Gemini: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Impossibile decodificare la risposta JSON di Gemini: {exc}"
            ) from exc
