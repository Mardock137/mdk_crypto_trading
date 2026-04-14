from __future__ import annotations

from src.agents.decision_maker import DecisionMakerAgent
from src.agents.execution_trader import ExecutionTraderAgent
from src.agents.market_analyst import MarketAnalystAgent
from src.agents.risk_manager import RiskManagerAgent
from src.core.runner import TradingRunner
from src.core.workflow import TradingWorkflow
from src.integrations.exchange.binance_client import BinanceClient
from src.integrations.llm_interfaces.anthropic_interface import AnthropicInterface
from src.integrations.llm_interfaces.gemini_interface import GeminiInterface
from src.integrations.llm_interfaces.openai_interface import OpenAiInterface
from src.utils.config import (
    load_llm_model_config,
    load_settings,
    load_symbol_config,
)
from src.utils.event_logger import EventLogger
from src.utils.logging_config import configure_logging
from src.utils.memory_manager import MemoryManager
from src.utils.telegram_notifier import TelegramNotifier


def main() -> None:
    settings = load_settings()
    logger = configure_logging(level=settings.log_level)
    event_logger = EventLogger()

    symbol_config = load_symbol_config()
    symbol = symbol_config["symbol"]
    quote_currency = symbol_config["quote_currency"]
    ma_config = load_llm_model_config("config/llm_models/market_analyst.yaml")
    dm_config = load_llm_model_config("config/llm_models/decision_maker.yaml")
    rm_config = load_llm_model_config("config/llm_models/risk_manager.yaml")

    # Client LLM per il Market Analyst
    ma_llm = AnthropicInterface(
        api_key=settings.claude_api_key or "",
        model=ma_config["model"],
        temperature=float(ma_config.get("temperature", 0.7)),
        max_tokens=ma_config.get("max_tokens"),
    )

    # Client LLM per il Decision Maker
    dm_llm = OpenAiInterface(
        api_key=settings.openai_api_key or "",
        model=dm_config["model"],
        temperature=float(dm_config.get("temperature", 0.2)),
        max_tokens=dm_config.get("max_tokens"),
        reasoning_effort=dm_config.get("reasoning_effort"),
    )

    # Client LLM per il Risk Manager
    rm_llm = GeminiInterface(
        api_key=settings.gemini_api_key or "",
        model=rm_config["model"],
        temperature=float(rm_config.get("temperature", 0.2)),
        max_tokens=rm_config.get("max_tokens"),
    )

    # Client exchange
    exchange_client = BinanceClient(settings, quote_currency=quote_currency)

    workflow = TradingWorkflow(
        market_analyst=MarketAnalystAgent(llm=ma_llm),
        decision_maker=DecisionMakerAgent(llm=dm_llm),
        risk_manager=RiskManagerAgent(llm=rm_llm),
        execution_trader=ExecutionTraderAgent(
            exchange_client=exchange_client,
            kill_switch=settings.kill_switch,
        ),
    )

    memory_manager = MemoryManager()

    telegram_notifier = TelegramNotifier(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
    )

    runner = TradingRunner(
        workflow=workflow,
        event_logger=event_logger,
        logger=logger,
        settings=settings,
        symbol=symbol,
        exchange_client=exchange_client,
        memory_manager=memory_manager,
        telegram_notifier=telegram_notifier,
    )

    runner.run()


if __name__ == "__main__":
    main()
