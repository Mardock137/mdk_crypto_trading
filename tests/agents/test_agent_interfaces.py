from pathlib import Path
from unittest.mock import MagicMock

from src.agents import (
    BaseAgent,
    DecisionMakerAgent,
    ExecutionTraderAgent,
    MarketAnalystAgent,
    RiskManagerAgent,
)


def test_all_agents_inherit_from_base_agent() -> None:
    assert issubclass(MarketAnalystAgent, BaseAgent)
    assert issubclass(DecisionMakerAgent, BaseAgent)
    assert issubclass(RiskManagerAgent, BaseAgent)
    assert issubclass(ExecutionTraderAgent, BaseAgent)


def test_agents_expose_expected_prompt_paths() -> None:
    agents = [
        (MarketAnalystAgent(llm=MagicMock()), "market_analyst.md"),
        (DecisionMakerAgent(llm=MagicMock()), "decision_maker.md"),
        (RiskManagerAgent(), "risk_manager.md"),
        (ExecutionTraderAgent(), "execution_trader.md"),
    ]

    for agent, prompt_name in agents:
        assert agent.prompt_path == Path("config") / "prompts" / prompt_name

