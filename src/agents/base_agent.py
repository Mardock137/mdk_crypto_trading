from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any, Generic, TypeVar

from src.integrations.llm_interfaces.base_llm_interface import BaseLlmInterface

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")

# base_agent.py si trova in src/agents/ — risalendo 3 livelli si arriva alla root del progetto
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class BaseAgent(ABC, Generic[InputT, OutputT]):
    def __init__(self, name: str, prompt_name: str = "") -> None:
        self.name = name
        self.prompt_name = prompt_name
        self._logger = logging.getLogger(f"mdk_crypto_trading.{name}")

    @property
    def prompt_path(self) -> Path | None:
        if not self.prompt_name:
            return None
        return _PROJECT_ROOT / "config" / "prompts" / self.prompt_name

    @abstractmethod
    def run(self, agent_input: InputT) -> OutputT:
        """Execute the agent with structured input."""

    def _call_llm_with_retry(
        self,
        llm: BaseLlmInterface,
        system_prompt: str,
        user_payload: dict[str, Any],
        parse_fn: Callable[[Any], OutputT],
        max_attempts: int = 4,
        base_delay: int = 2,
    ) -> OutputT:
        response = None
        for attempt in range(1, max_attempts + 1):
            try:
                response = llm.generate_json(system_prompt, user_payload)
                self._logger.debug("Risposta raw LLM: %s", response)
                return parse_fn(response)
            except (ValueError, KeyError, TypeError, RuntimeError) as exc:
                if attempt < max_attempts:
                    sleep_time = base_delay * (2 ** attempt)
                    self._logger.warning(
                        "Tentativo %d/%d — parsing fallito: %s | Risposta: %s | riprovo tra %ds",
                        attempt, max_attempts, exc, response, sleep_time,
                    )
                    time.sleep(sleep_time)
                else:
                    self._logger.warning(
                        "Tentativo %d/%d — parsing fallito: %s | Risposta: %s",
                        attempt, max_attempts, exc, response,
                    )
                    raise
        raise RuntimeError("Unexpected: retry loop completed without returning or raising")


def _ensure_list_of_str(value: Any, field_name: str) -> list[str]:
    """Normalizza un campo lista dalla risposta LLM in list[str].

    Gestisce: lista normale, stringa singola, tipo inatteso (ritorna lista vuota).
    """
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    return []


def unwrap_llm_response(data: Any) -> dict[str, Any]:
    """Normalizza la risposta LLM prima del parsing.

    Alcuni modelli restituiscono il JSON corretto ma wrappato in una lista
    (es. [{...}] invece di {...}). Questa funzione gestisce quel caso,
    oltre a rilevare risposte vuote o malformate.
    """
    if isinstance(data, list):
        if len(data) == 1 and isinstance(data[0], dict):
            return data[0]
        raise ValueError(
            f"Risposta LLM è una lista con {len(data)} elementi, atteso un dict singolo."
        )
    if isinstance(data, dict):
        if not data:
            raise ValueError("Risposta LLM è un dict vuoto.")
        return data
    raise ValueError(f"Tipo di risposta LLM non atteso: {type(data).__name__}.")

