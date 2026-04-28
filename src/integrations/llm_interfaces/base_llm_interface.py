from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping


class BaseLlmInterface(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the provider model name."""

    @abstractmethod
    def generate_json(
        self,
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Generate a structured JSON-like response."""

