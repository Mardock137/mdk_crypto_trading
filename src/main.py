from __future__ import annotations

from src.agents.decision_maker import DecisionMakerAgent
from src.agents.execution_trader import ExecutionTraderAgent
from src.agents.market_analyst import MarketAnalystAgent
from src.agents.risk_manager import RiskManagerAgent
from src.core.runner import TradingRunner
from src.core.workflow import TradingWorkflow
from src.utils.config import load_settings
from src.utils.event_logger import EventLogger
from src.utils.logging_config import configure_logging

_DEFAULT_SYMBOL = "BTCUSDC"


def main() -> None:
    settings = load_settings()
    logger = configure_logging(level=settings.log_level)
    event_logger = EventLogger()

    workflow = TradingWorkflow(
        market_analyst=MarketAnalystAgent(),
        decision_maker=DecisionMakerAgent(),
        risk_manager=RiskManagerAgent(),
        execution_trader=ExecutionTraderAgent(),
    )

    runner = TradingRunner(
        workflow=workflow,
        event_logger=event_logger,
        logger=logger,
        settings=settings,
        symbol=_DEFAULT_SYMBOL,
    )

    runner.run()


if __name__ == "__main__":
    main()
