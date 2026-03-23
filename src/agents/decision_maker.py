from __future__ import annotations

from src.agents.base_agent import BaseAgent
from src.core.contracts import DecisionMakerInput, TradeProposal


class DecisionMakerAgent(BaseAgent[DecisionMakerInput, TradeProposal]):
    def __init__(self) -> None:
        super().__init__(name="decision_maker", prompt_name="decision_maker.md")

    def run(self, agent_input: DecisionMakerInput) -> TradeProposal:
        raise NotImplementedError("DecisionMakerAgent.run() will be implemented in a later phase.")

