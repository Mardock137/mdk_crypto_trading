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
    """Classe base minimale comune a tutti gli agenti (LLM e non-LLM).

    Espone solo nome, prompt opzionale, logger e firma di `run`. Non sa nulla
    di LLM: gli agenti non-LLM (es. `ExecutionTraderAgent`) la estendono
    direttamente, mentre gli agenti LLM passano dalla classe intermedia
    `BaseLlmAgent` che aggiunge il flusso comune `run` + retry sul parsing.
    """

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


class BaseLlmAgent(BaseAgent[InputT, OutputT]):
    """Template Method per gli agenti che dialogano con un LLM.

    Centralizza il flusso comune in `run`:
      1. Verifica `prompt_path`.
      2. Legge il system prompt da disco.
      3. Costruisce il payload utente tramite `_build_user_payload` (astratto).
      4. Chiama l'LLM con retry sul parsing tramite `_call_llm_with_retry` e
         delega il parsing della risposta a `_parse_response` (astratto).

    Le sottoclassi implementano solo `_build_user_payload` (cosa mandare
    all'LLM) e `_parse_response` (come interpretare la risposta).
    """

    def __init__(
        self,
        name: str,
        prompt_name: str,
        llm: BaseLlmInterface,
    ) -> None:
        super().__init__(name=name, prompt_name=prompt_name)
        self._llm = llm

    def run(self, agent_input: InputT) -> OutputT:
        if self.prompt_path is None:
            raise RuntimeError(
                f"Prompt path non configurato per l'agente '{self.name}'.",
            )
        system_prompt = self.prompt_path.read_text(encoding="utf-8")
        user_payload = self._build_user_payload(agent_input)
        return self._call_llm_with_retry(
            system_prompt, user_payload, self._parse_response,
        )

    @abstractmethod
    def _build_user_payload(self, agent_input: InputT) -> dict[str, Any]:
        """Costruisce il payload utente da mandare all'LLM."""

    @abstractmethod
    def _parse_response(self, data: Any) -> OutputT:
        """Interpreta la risposta JSON dell'LLM e produce l'output dell'agente."""

    def _call_llm_with_retry(
        self,
        system_prompt: str,
        user_payload: dict[str, Any],
        parse_fn: Callable[[Any], OutputT],
        max_attempts: int = 4,
        base_delay: int = 2,
    ) -> OutputT:
        response = None
        for attempt in range(1, max_attempts + 1):
            try:
                response = self._llm.generate_json(system_prompt, user_payload)
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


def ensure_list_of_str(value: Any) -> list[str]:
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
