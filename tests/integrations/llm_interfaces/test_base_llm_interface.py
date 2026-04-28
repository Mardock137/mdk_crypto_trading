from typing import Any, Mapping

from src.integrations.llm_interfaces.base_llm_interface import BaseLlmInterface


class DummyLlmInterface(BaseLlmInterface):
    @property
    def model_name(self) -> str:
        return "dummy-model"

    def generate_json(
        self,
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {
            "system_prompt": system_prompt,
            "user_payload": dict(user_payload),
        }


def test_base_llm_interface_can_be_implemented() -> None:
    interface = DummyLlmInterface()

    assert interface.model_name == "dummy-model"
    assert interface.generate_json("system", {"foo": "bar"}) == {
        "system_prompt": "system",
        "user_payload": {"foo": "bar"},
    }

