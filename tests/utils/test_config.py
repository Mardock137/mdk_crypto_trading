import pytest

from src.utils.config import TradingMode, load_settings


def test_load_settings_reads_required_values() -> None:
    settings = load_settings(
        {
            "TRADING_MODE": "DEMO",
            "KILL_SWITCH": "1",
            "CYCLE_INTERVAL_SECONDS": "7200",
            "OPENAI_API_KEY": "openai-key",
            "GEMINI_API_KEY": "gemini-key",
        }
    )

    assert settings.trading_mode is TradingMode.DEMO
    assert settings.kill_switch is True
    assert settings.cycle_interval_seconds == 7200
    assert settings.openai_api_key == "openai-key"
    assert settings.gemini_api_key == "gemini-key"


def test_load_settings_requires_trading_mode() -> None:
    with pytest.raises(ValueError):
        load_settings({"CYCLE_INTERVAL_SECONDS": "7200"})


def test_load_settings_rejects_invalid_boolean_values() -> None:
    with pytest.raises(ValueError):
        load_settings(
            {
                "TRADING_MODE": "DEMO",
                "KILL_SWITCH": "maybe",
                "CYCLE_INTERVAL_SECONDS": "7200",
            }
        )

