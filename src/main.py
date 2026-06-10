from __future__ import annotations

from pathlib import Path

from src.agents.decision_maker import DecisionMakerAgent
from src.agents.execution_trader import ExecutionTraderAgent
from src.agents.market_analyst import MarketAnalystAgent
from src.agents.performance_reviewer import PerformanceReviewerAgent
from src.agents.risk_manager import RiskManagerAgent
from src.core.runner import TradingRunner
from src.core.workflow import TradingWorkflow
from src.integrations.exchange.binance_client import BinanceClient
from src.integrations.llm_interfaces.anthropic_interface import AnthropicInterface
from src.integrations.llm_interfaces.gemini_interface import GeminiInterface
from src.integrations.llm_interfaces.openai_interface import OpenAiInterface
from src.utils.config import (
    AppSettings,
    load_llm_model_config,
    load_settings,
    load_symbol_config,
)
from src.utils.event_logger import EventLogger
from src.utils.logging_config import configure_logging
from src.utils.memory_manager import MemoryManager
from src.utils.telegram_notifier import TelegramNotifier

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def build_runner(settings: AppSettings) -> TradingRunner:
    """Assembla e restituisce un TradingRunner configurato e pronto per il loop."""
    logger = configure_logging(level=settings.log_level)
    event_logger = EventLogger()

    symbol_config = load_symbol_config()
    symbol = symbol_config["symbol"]
    quote_currency = symbol_config["quote_currency"]
    ma_config = load_llm_model_config(_PROJECT_ROOT / "config/llm_models/market_analyst.yaml")
    dm_config = load_llm_model_config(_PROJECT_ROOT / "config/llm_models/decision_maker.yaml")
    rm_config = load_llm_model_config(_PROJECT_ROOT / "config/llm_models/risk_manager.yaml")
    pr_config = load_llm_model_config(_PROJECT_ROOT / "config/llm_models/performance_reviewer.yaml")

    required_keys = {
        "OPENAI_API_KEY": settings.openai_api_key,
        "CLAUDE_API_KEY": settings.claude_api_key,
        "GEMINI_API_KEY": settings.gemini_api_key,
    }
    missing = [name for name, value in required_keys.items() if not value]
    if missing:
        raise ValueError(
            f"API key obbligatorie non configurate nel .env: {', '.join(missing)}"
        )

    # Client LLM per il Market Analyst (GPT-5.4, senza reasoning: analisi tecnica strutturata)
    ma_llm = OpenAiInterface(
        api_key=settings.openai_api_key,
        model=ma_config["model"],
        temperature=float(ma_config["temperature"]),
        max_tokens=ma_config.get("max_tokens"),
    )

    # Client LLM per il Decision Maker (Claude Opus 4.8 con adaptive thinking)
    # Nota: `temperature` non e accettata da Opus 4.8 con thinking abilitato,
    # quindi non viene passata: l'interfaccia la ignora quando `thinking_effort` e valorizzato.
    dm_llm = AnthropicInterface(
        api_key=settings.claude_api_key,
        model=dm_config["model"],
        max_tokens=dm_config.get("max_tokens"),
        thinking_effort=dm_config.get("thinking_effort"),
    )

    # Client LLM per il Risk Manager
    _rm_temp_raw = rm_config.get("temperature")
    rm_llm = GeminiInterface(
        api_key=settings.gemini_api_key,
        model=rm_config["model"],
        temperature=float(_rm_temp_raw) if _rm_temp_raw is not None else None,
        max_tokens=rm_config.get("max_tokens"),
    )

    # Client LLM per il Performance Reviewer (riutilizza AnthropicInterface)
    pr_llm = AnthropicInterface(
        api_key=settings.claude_api_key,
        model=pr_config["model"],
        temperature=float(pr_config["temperature"]),
        max_tokens=pr_config.get("max_tokens"),
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
    performance_reviewer = PerformanceReviewerAgent(llm=pr_llm)

    telegram_notifier = TelegramNotifier(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
    )

    return TradingRunner(
        workflow=workflow,
        event_logger=event_logger,
        logger=logger,
        settings=settings,
        symbol=symbol,
        exchange_client=exchange_client,
        memory_manager=memory_manager,
        performance_reviewer=performance_reviewer,
        telegram_notifier=telegram_notifier,
    )


def main() -> None:
    settings = load_settings()
    runner = build_runner(settings)
    runner.run()


if __name__ == "__main__":
    main()
