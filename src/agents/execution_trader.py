from __future__ import annotations

from src.agents.base_agent import BaseAgent
from src.core.contracts import ExecutionInput, ExecutionReport


class ExecutionTraderAgent(BaseAgent[ExecutionInput, ExecutionReport]):
    def __init__(self) -> None:
        super().__init__(name="execution_trader", prompt_name="execution_trader.md")

    def run(self, agent_input: ExecutionInput) -> ExecutionReport:
        raise NotImplementedError("ExecutionTraderAgent.run() will be implemented in a later phase.")

