from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.agents import (
    BaseAgent,
    DecisionMakerAgent,
    ExecutionTraderAgent,
    MarketAnalystAgent,
    RiskManagerAgent,
)
from src.agents.base_agent import _ensure_list_of_str, unwrap_llm_response


def test_all_agents_inherit_from_base_agent() -> None:
    assert issubclass(MarketAnalystAgent, BaseAgent)
    assert issubclass(DecisionMakerAgent, BaseAgent)
    assert issubclass(RiskManagerAgent, BaseAgent)
    assert issubclass(ExecutionTraderAgent, BaseAgent)


def test_agents_expose_expected_prompt_paths() -> None:
    agents_with_prompts = [
        (MarketAnalystAgent(llm=MagicMock()), "market_analyst.md"),
        (DecisionMakerAgent(llm=MagicMock()), "decision_maker.md"),
        (RiskManagerAgent(llm=MagicMock()), "risk_manager.md"),
    ]

    for agent, prompt_name in agents_with_prompts:
        assert agent.prompt_path is not None
        assert agent.prompt_path.is_absolute()
        assert agent.prompt_path.name == prompt_name
        assert "config" in agent.prompt_path.parts
        assert "prompts" in agent.prompt_path.parts


def test_execution_trader_prompt_path_is_none() -> None:
    agent = ExecutionTraderAgent(exchange_client=MagicMock())
    assert agent.prompt_path is None


# --- Test _ensure_list_of_str ---

def test_ensure_list_of_str_with_normal_list() -> None:
    assert _ensure_list_of_str(["a", "b", "c"], "field") == ["a", "b", "c"]


def test_ensure_list_of_str_converts_items_to_str() -> None:
    assert _ensure_list_of_str([1, 2.5, True], "field") == ["1", "2.5", "True"]


def test_ensure_list_of_str_with_single_string() -> None:
    assert _ensure_list_of_str("solo", "field") == ["solo"]


def test_ensure_list_of_str_with_unexpected_type_returns_empty() -> None:
    assert _ensure_list_of_str(42, "field") == []
    assert _ensure_list_of_str(None, "field") == []
    assert _ensure_list_of_str({"key": "val"}, "field") == []


# --- Test unwrap_llm_response ---

def test_unwrap_dict_normale() -> None:
    data = {"key": "value"}
    assert unwrap_llm_response(data) == {"key": "value"}


def test_unwrap_lista_con_un_dict() -> None:
    data = [{"key": "value"}]
    assert unwrap_llm_response(data) == {"key": "value"}


def test_unwrap_dict_vuoto_raises() -> None:
    with pytest.raises(ValueError, match="dict vuoto"):
        unwrap_llm_response({})


def test_unwrap_lista_vuota_raises() -> None:
    with pytest.raises(ValueError, match="0 elementi"):
        unwrap_llm_response([])


def test_unwrap_lista_multipla_raises() -> None:
    with pytest.raises(ValueError, match="2 elementi"):
        unwrap_llm_response([{"a": 1}, {"b": 2}])


def test_unwrap_tipo_non_atteso_raises() -> None:
    with pytest.raises(ValueError, match="non atteso"):
        unwrap_llm_response("stringa")

