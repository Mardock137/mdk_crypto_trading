from __future__ import annotations

import json
import logging
from typing import Any, Mapping
from unittest.mock import MagicMock

from src.integrations.llm_interfaces.base_llm_interface import BaseLlmInterface


class DummyLlmInterface(BaseLlmInterface):
    """Implementazione minima per testare end-to-end il Template Method della base."""

    _PROVIDER_NAME = "Dummy"
    _RETRYABLE_ERRORS: tuple[type[BaseException], ...] = ()
    _NON_RETRYABLE_PROVIDER_ERROR: type[BaseException] = RuntimeError

    def __init__(self) -> None:
        self._fake_logger = MagicMock(spec=logging.Logger)

    @property
    def model_name(self) -> str:
        return "dummy-model"

    @property
    def _logger(self) -> logging.Logger:
        return self._fake_logger

    def _call_provider(
        self,
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> Any:
        return json.dumps(
            {"system_prompt": system_prompt, "user_payload": dict(user_payload)},
        )

    def _extract_text(self, response: Any) -> str:
        return str(response)

    def _log_empty_response(self, response: Any) -> None:
        self._fake_logger.warning("Dummy risposta vuota | response: %s", response)


def test_base_llm_interface_can_be_implemented() -> None:
    """La base deve essere istanziabile da una sottoclasse concreta minimale e generate_json
    (template method) deve orchestrare la chiamata al provider e il parsing JSON."""
    interface = DummyLlmInterface()

    assert interface.model_name == "dummy-model"
    assert interface.generate_json("system", {"foo": "bar"}) == {
        "system_prompt": "system",
        "user_payload": {"foo": "bar"},
    }
