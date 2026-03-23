from __future__ import annotations

from src.agents.base_agent import BaseAgent
from src.core.contracts import RiskAssessment, RiskManagerInput


class RiskManagerAgent(BaseAgent[RiskManagerInput, RiskAssessment]):
    def __init__(self) -> None:
        super().__init__(name="risk_manager", prompt_name="risk_manager.md")

    def run(self, agent_input: RiskManagerInput) -> RiskAssessment:
        raise NotImplementedError("RiskManagerAgent.run() will be implemented in a later phase.")

