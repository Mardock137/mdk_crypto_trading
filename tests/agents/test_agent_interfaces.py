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
from src.agents.base_agent import unwrap_llm_response


def test_all_agents_inherit_from_base_agent() -> None:
    assert issubclass(MarketAnalystAgent, BaseAgent)
    assert issubclass(DecisionMakerAgent, BaseAgent)
    assert issubclass(RiskManagerAgent, BaseAgent)
    assert issubclass(ExecutionTraderAgent, BaseAgent)


def test_agents_expose_expected_prompt_paths() -> None:
    agents = [
        (MarketAnalystAgent(llm=MagicMock()), "market_analyst.md"),
        (DecisionMakerAgent(llm=MagicMock()), "decision_maker.md"),
        (RiskManagerAgent(llm=MagicMock()), "risk_manager.md"),
        (ExecutionTraderAgent(exchange_client=MagicMock()), "execution_trader.md"),
    ]

    for agent, prompt_name in agents:
        assert agent.prompt_path == Path("config") / "prompts" / prompt_name


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

