from __future__ import annotations

from src.agents.base_agent import BaseAgent
from src.core.contracts import MarketAnalysis, MarketAnalystInput


class MarketAnalystAgent(BaseAgent[MarketAnalystInput, MarketAnalysis]):
    def __init__(self) -> None:
        super().__init__(name="market_analyst", prompt_name="market_analyst.md")

    def run(self, agent_input: MarketAnalystInput) -> MarketAnalysis:
        raise NotImplementedError("MarketAnalystAgent.run() will be implemented in a later phase.")

