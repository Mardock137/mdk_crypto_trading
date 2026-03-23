from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar


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

