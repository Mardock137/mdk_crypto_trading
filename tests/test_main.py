"""Test di integrazione per main(): verifica che il bootstrap assembli tutto correttamente."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import MagicMock, patch

import pytest

from src.main import build_runner, main
from src.utils.config import AppSettings, TradingMode


_FAKE_SETTINGS = AppSettings(
    trading_mode=TradingMode.DEMO,
    kill_switch=False,
    cycle_interval_seconds=60,
    openai_api_key="openai-test-key",
    gemini_api_key="gemini-test-key",
    claude_api_key="claude-test-key",
    binance_api_key=None,
    binance_secret_key=None,
    binance_demo_api_key="demo-key",
    binance_demo_secret_key="demo-secret",
    binance_demo_base_url="https://demo-api.binance.com/api",
    log_level="INFO",
    telegram_bot_token="tg-token-test",
    telegram_chat_id="tg-chat-test",
)

_FAKE_LLM_CONFIG = {"model": "gpt-test", "temperature": 0.2, "max_tokens": 512}


@patch("src.main.configure_logging")
@patch("src.main.TelegramNotifier")
@patch("src.main.TradingRunner")
@patch("src.main.BinanceClient")
@patch("src.main.GeminiInterface")
@patch("src.main.AnthropicInterface")
@patch("src.main.OpenAiInterface")
@patch("src.main.load_llm_model_config", return_value=_FAKE_LLM_CONFIG)
@patch("src.main.load_symbol_config", return_value={"symbol": "BTCUSDC", "quote_currency": "USDC"})
@patch("src.main.load_settings", return_value=_FAKE_SETTINGS)
def test_main_calls_runner_run(
    mock_load_settings: MagicMock,
    mock_load_symbol: MagicMock,
    mock_load_llm: MagicMock,
    mock_openai_cls: MagicMock,
    mock_anthropic_cls: MagicMock,
    mock_gemini_cls: MagicMock,
    mock_binance_cls: MagicMock,
    mock_runner_cls: MagicMock,
    mock_telegram_cls: MagicMock,
    mock_configure_logging: MagicMock,
) -> None:
    """main() deve costruire il runner e chiamare run()."""
    main()

    mock_runner_cls.return_value.run.assert_called_once()


@patch("src.main.configure_logging")
@patch("src.main.TelegramNotifier")
@patch("src.main.TradingRunner")
@patch("src.main.BinanceClient")
@patch("src.main.GeminiInterface")
@patch("src.main.AnthropicInterface")
@patch("src.main.OpenAiInterface")
@patch("src.main.load_llm_model_config", return_value=_FAKE_LLM_CONFIG)
@patch("src.main.load_symbol_config", return_value={"symbol": "BTCUSDC", "quote_currency": "USDC"})
@patch("src.main.load_settings", return_value=_FAKE_SETTINGS)
def test_main_creates_openai_interface_once(
    mock_load_settings: MagicMock,
    mock_load_symbol: MagicMock,
    mock_load_llm: MagicMock,
    mock_openai_cls: MagicMock,
    mock_anthropic_cls: MagicMock,
    mock_gemini_cls: MagicMock,
    mock_binance_cls: MagicMock,
    mock_runner_cls: MagicMock,
    mock_telegram_cls: MagicMock,
    mock_configure_logging: MagicMock,
) -> None:
    """OpenAiInterface deve essere istanziata 1 volta (solo Market Analyst)."""
    main()

    mock_openai_cls.assert_called_once()


@patch("src.main.configure_logging")
@patch("src.main.TelegramNotifier")
@patch("src.main.TradingRunner")
@patch("src.main.BinanceClient")
@patch("src.main.GeminiInterface")
@patch("src.main.AnthropicInterface")
@patch("src.main.OpenAiInterface")
@patch("src.main.load_llm_model_config", return_value=_FAKE_LLM_CONFIG)
@patch("src.main.load_symbol_config", return_value={"symbol": "BTCUSDC", "quote_currency": "USDC"})
@patch("src.main.load_settings", return_value=_FAKE_SETTINGS)
def test_main_creates_anthropic_interface_once(
    mock_load_settings: MagicMock,
    mock_load_symbol: MagicMock,
    mock_load_llm: MagicMock,
    mock_openai_cls: MagicMock,
    mock_anthropic_cls: MagicMock,
    mock_gemini_cls: MagicMock,
    mock_binance_cls: MagicMock,
    mock_runner_cls: MagicMock,
    mock_telegram_cls: MagicMock,
    mock_configure_logging: MagicMock,
) -> None:
    """AnthropicInterface deve essere istanziata 2 volte (Decision Maker + Performance Reviewer)."""
    main()

    assert mock_anthropic_cls.call_count == 2


@patch("src.main.configure_logging")
@patch("src.main.TelegramNotifier")
@patch("src.main.TradingRunner")
@patch("src.main.BinanceClient")
@patch("src.main.GeminiInterface")
@patch("src.main.AnthropicInterface")
@patch("src.main.OpenAiInterface")
@patch("src.main.load_llm_model_config", return_value=_FAKE_LLM_CONFIG)
@patch("src.main.load_symbol_config", return_value={"symbol": "BTCUSDC", "quote_currency": "USDC"})
@patch("src.main.load_settings", return_value=_FAKE_SETTINGS)
def test_main_creates_gemini_interface_once(
    mock_load_settings: MagicMock,
    mock_load_symbol: MagicMock,
    mock_load_llm: MagicMock,
    mock_openai_cls: MagicMock,
    mock_anthropic_cls: MagicMock,
    mock_gemini_cls: MagicMock,
    mock_binance_cls: MagicMock,
    mock_runner_cls: MagicMock,
    mock_telegram_cls: MagicMock,
    mock_configure_logging: MagicMock,
) -> None:
    """GeminiInterface deve essere istanziata 1 volta (Risk Manager)."""
    main()

    mock_gemini_cls.assert_called_once()


@patch("src.main.configure_logging")
@patch("src.main.TelegramNotifier")
@patch("src.main.TradingRunner")
@patch("src.main.BinanceClient")
@patch("src.main.GeminiInterface")
@patch("src.main.AnthropicInterface")
@patch("src.main.OpenAiInterface")
@patch("src.main.load_llm_model_config", return_value=_FAKE_LLM_CONFIG)
@patch("src.main.load_symbol_config", return_value={"symbol": "BTCUSDC", "quote_currency": "USDC"})
@patch("src.main.load_settings", return_value=_FAKE_SETTINGS)
def test_main_loads_three_llm_configs(
    mock_load_settings: MagicMock,
    mock_load_symbol: MagicMock,
    mock_load_llm: MagicMock,
    mock_openai_cls: MagicMock,
    mock_anthropic_cls: MagicMock,
    mock_gemini_cls: MagicMock,
    mock_binance_cls: MagicMock,
    mock_runner_cls: MagicMock,
    mock_telegram_cls: MagicMock,
    mock_configure_logging: MagicMock,
) -> None:
    """load_llm_model_config deve essere chiamata 4 volte (MA, DM, RM, PR)."""
    main()

    assert mock_load_llm.call_count == 4
    paths_called = [str(c.args[0]) for c in mock_load_llm.call_args_list]
    assert any("market_analyst" in p for p in paths_called)
    assert any("decision_maker" in p for p in paths_called)
    assert any("risk_manager" in p for p in paths_called)
    assert any("performance_reviewer" in p for p in paths_called)


@patch("src.main.configure_logging")
@patch("src.main.TelegramNotifier")
@patch("src.main.TradingRunner")
@patch("src.main.BinanceClient")
@patch("src.main.GeminiInterface")
@patch("src.main.AnthropicInterface")
@patch("src.main.OpenAiInterface")
@patch("src.main.load_llm_model_config", return_value=_FAKE_LLM_CONFIG)
@patch("src.main.load_symbol_config", return_value={"symbol": "BTCUSDC", "quote_currency": "USDC"})
@patch("src.main.load_settings", return_value=_FAKE_SETTINGS)
def test_main_creates_binance_client_with_settings(
    mock_load_settings: MagicMock,
    mock_load_symbol: MagicMock,
    mock_load_llm: MagicMock,
    mock_openai_cls: MagicMock,
    mock_anthropic_cls: MagicMock,
    mock_gemini_cls: MagicMock,
    mock_binance_cls: MagicMock,
    mock_runner_cls: MagicMock,
    mock_telegram_cls: MagicMock,
    mock_configure_logging: MagicMock,
) -> None:
    """BinanceClient deve essere istanziato con le settings caricate."""
    main()

    mock_binance_cls.assert_called_once_with(_FAKE_SETTINGS, quote_currency="USDC")


@patch("src.main.configure_logging")
@patch("src.main.TelegramNotifier")
@patch("src.main.TradingRunner")
@patch("src.main.BinanceClient")
@patch("src.main.GeminiInterface")
@patch("src.main.AnthropicInterface")
@patch("src.main.OpenAiInterface")
@patch("src.main.load_llm_model_config", return_value=_FAKE_LLM_CONFIG)
@patch("src.main.load_symbol_config", return_value={"symbol": "BTCUSDC", "quote_currency": "USDC"})
@patch("src.main.load_settings", return_value=_FAKE_SETTINGS)
def test_main_creates_telegram_notifier(
    mock_load_settings: MagicMock,
    mock_load_symbol: MagicMock,
    mock_load_llm: MagicMock,
    mock_openai_cls: MagicMock,
    mock_anthropic_cls: MagicMock,
    mock_gemini_cls: MagicMock,
    mock_binance_cls: MagicMock,
    mock_runner_cls: MagicMock,
    mock_telegram_cls: MagicMock,
    mock_configure_logging: MagicMock,
) -> None:
    """TelegramNotifier deve essere istanziato con token e chat_id dalle settings."""
    main()

    mock_telegram_cls.assert_called_once_with(
        bot_token="tg-token-test",
        chat_id="tg-chat-test",
    )


@patch("src.main.configure_logging")
@patch("src.main.load_llm_model_config", return_value=_FAKE_LLM_CONFIG)
@patch("src.main.load_symbol_config", return_value={"symbol": "BTCUSDC", "quote_currency": "USDC"})
@patch("src.main.load_settings", return_value=replace(_FAKE_SETTINGS, openai_api_key=None))
def test_main_raises_if_required_api_key_is_missing(
    mock_load_settings: MagicMock,
    mock_load_symbol: MagicMock,
    mock_load_llm: MagicMock,
    mock_configure_logging: MagicMock,
) -> None:
    """main() deve fallire subito se manca una API key LLM obbligatoria."""
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        main()


# ---------- Test diretti su build_runner ----------


@patch("src.main.configure_logging")
@patch("src.main.TelegramNotifier")
@patch("src.main.TradingRunner")
@patch("src.main.BinanceClient")
@patch("src.main.GeminiInterface")
@patch("src.main.AnthropicInterface")
@patch("src.main.OpenAiInterface")
@patch("src.main.load_llm_model_config", return_value=_FAKE_LLM_CONFIG)
@patch("src.main.load_symbol_config", return_value={"symbol": "BTCUSDC", "quote_currency": "USDC"})
def test_build_runner_returns_trading_runner(
    mock_load_symbol: MagicMock,
    mock_load_llm: MagicMock,
    mock_openai_cls: MagicMock,
    mock_anthropic_cls: MagicMock,
    mock_gemini_cls: MagicMock,
    mock_binance_cls: MagicMock,
    mock_runner_cls: MagicMock,
    mock_telegram_cls: MagicMock,
    mock_configure_logging: MagicMock,
) -> None:
    """build_runner() deve istanziare TradingRunner e restituirlo."""
    result = build_runner(_FAKE_SETTINGS)

    mock_runner_cls.assert_called_once()
    assert result is mock_runner_cls.return_value


@patch("src.main.configure_logging")
@patch("src.main.load_llm_model_config", return_value=_FAKE_LLM_CONFIG)
@patch("src.main.load_symbol_config", return_value={"symbol": "BTCUSDC", "quote_currency": "USDC"})
def test_build_runner_raises_if_required_api_key_is_missing(
    mock_load_symbol: MagicMock,
    mock_load_llm: MagicMock,
    mock_configure_logging: MagicMock,
) -> None:
    """build_runner() deve sollevare ValueError se manca una API key LLM obbligatoria."""
    settings_no_key = replace(_FAKE_SETTINGS, openai_api_key=None)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        build_runner(settings_no_key)
