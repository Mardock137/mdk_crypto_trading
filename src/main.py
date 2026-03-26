from __future__ import annotations

from src.agents.decision_maker import DecisionMakerAgent
from src.agents.execution_trader import ExecutionTraderAgent
from src.agents.market_analyst import MarketAnalystAgent
from src.agents.risk_manager import RiskManagerAgent
from src.core.runner import TradingRunner
from src.core.workflow import TradingWorkflow
from src.integrations.exchange.binance_client import BinanceClient
from src.integrations.llm_interfaces.openai_interface import OpenAiInterface
from src.utils.config import (
    load_llm_model_config,
    load_settings,
    load_symbol_config,
)
from src.utils.event_logger import EventLogger
from src.utils.logging_config import configure_logging


def main() -> None:
    settings = load_settings()
    logger = configure_logging(level=settings.log_level)
    event_logger = EventLogger()

    symbol = load_symbol_config()
    ma_config = load_llm_model_config("config/llm_models/market_analyst.yaml")

    # Client LLM per il Market Analyst
    openai_llm = OpenAiInterface(
        api_key=settings.openai_api_key or "",
        model=ma_config["model"],
        temperature=float(ma_config.get("temperature", 0.7)),
        max_tokens=ma_config.get("max_tokens"),
    )

    # Client exchange
    exchange_client = BinanceClient(settings)

    workflow = TradingWorkflow(
        market_analyst=MarketAnalystAgent(llm=openai_llm),
        decision_maker=DecisionMakerAgent(),
        risk_manager=RiskManagerAgent(),
        execution_trader=ExecutionTraderAgent(),
    )

    runner = TradingRunner(
        workflow=workflow,
        event_logger=event_logger,
        logger=logger,
        settings=settings,
        symbol=symbol,
        exchange_client=exchange_client,
    )

    runner.run()


if __name__ == "__main__":
    main()
