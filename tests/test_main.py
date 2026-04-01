"""Test di integrazione per main(): verifica che il bootstrap assembli tutto correttamente."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

from src.main import main
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
)

_FAKE_LLM_CONFIG = {"model": "gpt-test", "temperature": 0.2, "max_tokens": 512}


@patch("src.main.TradingRunner")
@patch("src.main.BinanceClient")
@patch("src.main.GeminiInterface")
@patch("src.main.AnthropicInterface")
@patch("src.main.OpenAiInterface")
@patch("src.main.load_llm_model_config", return_value=_FAKE_LLM_CONFIG)
@patch("src.main.load_symbol_config", return_value="BTCUSDC")
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
) -> None:
    """main() deve costruire il runner e chiamare run()."""
    main()

    mock_runner_cls.return_value.run.assert_called_once()


@patch("src.main.TradingRunner")
@patch("src.main.BinanceClient")
@patch("src.main.GeminiInterface")
@patch("src.main.AnthropicInterface")
@patch("src.main.OpenAiInterface")
@patch("src.main.load_llm_model_config", return_value=_FAKE_LLM_CONFIG)
@patch("src.main.load_symbol_config", return_value="BTCUSDC")
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
) -> None:
    """OpenAiInterface deve essere istanziata 1 volta (solo Decision Maker)."""
    main()

    mock_openai_cls.assert_called_once()


@patch("src.main.TradingRunner")
@patch("src.main.BinanceClient")
@patch("src.main.GeminiInterface")
@patch("src.main.AnthropicInterface")
@patch("src.main.OpenAiInterface")
@patch("src.main.load_llm_model_config", return_value=_FAKE_LLM_CONFIG)
@patch("src.main.load_symbol_config", return_value="BTCUSDC")
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
) -> None:
    """AnthropicInterface deve essere istanziata 1 volta (Market Analyst)."""
    main()

    mock_anthropic_cls.assert_called_once()


@patch("src.main.TradingRunner")
@patch("src.main.BinanceClient")
@patch("src.main.GeminiInterface")
@patch("src.main.AnthropicInterface")
@patch("src.main.OpenAiInterface")
@patch("src.main.load_llm_model_config", return_value=_FAKE_LLM_CONFIG)
@patch("src.main.load_symbol_config", return_value="BTCUSDC")
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
) -> None:
    """GeminiInterface deve essere istanziata 1 volta (Risk Manager)."""
    main()

    mock_gemini_cls.assert_called_once()


@patch("src.main.TradingRunner")
@patch("src.main.BinanceClient")
@patch("src.main.GeminiInterface")
@patch("src.main.AnthropicInterface")
@patch("src.main.OpenAiInterface")
@patch("src.main.load_llm_model_config", return_value=_FAKE_LLM_CONFIG)
@patch("src.main.load_symbol_config", return_value="BTCUSDC")
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
) -> None:
    """load_llm_model_config deve essere chiamata 3 volte (MA, DM, RM)."""
    main()

    assert mock_load_llm.call_count == 3
    paths_called = [c.args[0] for c in mock_load_llm.call_args_list]
    assert any("market_analyst" in p for p in paths_called)
    assert any("decision_maker" in p for p in paths_called)
    assert any("risk_manager" in p for p in paths_called)


@patch("src.main.TradingRunner")
@patch("src.main.BinanceClient")
@patch("src.main.GeminiInterface")
@patch("src.main.AnthropicInterface")
@patch("src.main.OpenAiInterface")
@patch("src.main.load_llm_model_config", return_value=_FAKE_LLM_CONFIG)
@patch("src.main.load_symbol_config", return_value="BTCUSDC")
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
) -> None:
    """BinanceClient deve essere istanziato con le settings caricate."""
    main()

    mock_binance_cls.assert_called_once_with(_FAKE_SETTINGS)
