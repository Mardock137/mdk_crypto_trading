from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Mapping

from src.core.exceptions import LlmError
from src.utils.log_utils import truncate_for_log

from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class BaseLlmInterface(ABC):
    """Template Method per le interfacce LLM.

    Centralizza in `generate_json` lo scheletro comune a tutti i provider:
    retry su errori transienti, estrazione testo, controllo risposta vuota,
    parsing JSON, controllo dict vuoto e wrapping degli errori non retryable.

    Le sottoclassi devono dichiarare gli attributi di classe
    `_PROVIDER_NAME`, `_RETRYABLE_ERRORS`, `_NON_RETRYABLE_PROVIDER_ERROR` e
    implementare i metodi astratti `_call_provider`, `_extract_text`,
    `_log_empty_response` (oltre alla property `_logger` che espone il logger
    a livello modulo, per consentire ai test di patcharlo).

    L'hook `_strip_response` ha default no-op: solo il provider che ne ha
    bisogno (Anthropic) ne fa override per togliere wrapping markdown.
    """

    _PROVIDER_NAME: ClassVar[str] = ""
    _RETRYABLE_ERRORS: ClassVar[tuple[type[BaseException], ...]] = ()
    _NON_RETRYABLE_PROVIDER_ERROR: ClassVar[type[BaseException]] = Exception

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the provider model name."""

    @property
    @abstractmethod
    def _logger(self) -> logging.Logger:
        """Logger del modulo della sottoclasse (risolto dinamicamente per i test)."""

    @abstractmethod
    def _call_provider(
        self,
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> Any:
        """Chiamata effettiva all'SDK del provider."""

    @abstractmethod
    def _extract_text(self, response: Any) -> str:
        """Estrae il testo grezzo dalla risposta del provider."""

    @abstractmethod
    def _log_empty_response(self, response: Any) -> None:
        """Logga il warning con i metadati provider-specific (stop_reason, finish_reason, ecc.)."""

    def _strip_response(self, raw: str) -> str:
        """Hook opzionale per ripulire la risposta prima del parsing JSON.

        Default: no-op. Anthropic ne fa override per togliere il wrapping
        markdown (```json ... ```).
        """
        return raw

    def generate_json(
        self,
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Genera una risposta JSON dal provider, con retry su errori transienti."""
        retrying = Retrying(
            retry=retry_if_exception_type(self._RETRYABLE_ERRORS),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            stop=stop_after_attempt(3),
            reraise=True,
        )
        for attempt in retrying:
            with attempt:
                return self._generate_json_once(system_prompt, user_payload)
        raise LlmError("Unexpected: Retrying loop completed without returning.")

    def _generate_json_once(
        self,
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        stripped: str = ""
        try:
            response = self._call_provider(system_prompt, user_payload)
            raw = self._extract_text(response)
            if not raw or not raw.strip():
                self._log_empty_response(response)
                raise LlmError(
                    f"Risposta vuota dal provider {self._PROVIDER_NAME}.",
                )
            stripped = self._strip_response(raw)
            result: dict[str, Any] = json.loads(stripped)
            if not result:
                raise LlmError(
                    f"Il provider {self._PROVIDER_NAME} ha risposto con un JSON vuoto.",
                )
            return result
        except self._RETRYABLE_ERRORS:
            raise
        except self._NON_RETRYABLE_PROVIDER_ERROR as exc:
            raise LlmError(
                f"Errore API {self._PROVIDER_NAME}: {exc}",
            ) from exc
        except json.JSONDecodeError as exc:
            self._logger.warning(
                "Risposta non decodificabile di %s (troncata): %s",
                self._PROVIDER_NAME,
                truncate_for_log(stripped),
            )
            raise LlmError(
                f"Impossibile decodificare la risposta JSON di {self._PROVIDER_NAME}: {exc}",
            ) from exc
