from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar


InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class BaseAgent(ABC, Generic[InputT, OutputT]):
    def __init__(self, name: str, prompt_name: str) -> None:
        self.name = name
        self.prompt_name = prompt_name

    @property
    def prompt_path(self) -> Path:
        return Path("config") / "prompts" / self.prompt_name

    @abstractmethod
    def run(self, agent_input: InputT) -> OutputT:
        """Execute the agent with structured input."""


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
            f"Risposta LLM e una lista con {len(data)} elementi, atteso un dict singolo."
        )
    if isinstance(data, dict):
        if not data:
            raise ValueError("Risposta LLM e un dict vuoto.")
        return data
    raise ValueError(f"Tipo di risposta LLM non atteso: {type(data).__name__}.")

