from pathlib import Path

import pytest

from src.utils.config import (
    TradingMode,
    load_llm_model_config,
    load_settings,
    load_symbol_config,
    load_trading_config,
)


def test_load_settings_reads_required_values() -> None:
    settings = load_settings(
        {
            "TRADING_MODE": "DEMO",
            "KILL_SWITCH": "1",
            "CYCLE_INTERVAL_SECONDS": "7200",
            "OPENAI_API_KEY": "openai-key",
            "GEMINI_API_KEY": "gemini-key",
            "CLAUDE_API_KEY": "claude-key",
        }
    )

    assert settings.trading_mode is TradingMode.DEMO
    assert settings.kill_switch is True
    assert settings.cycle_interval_seconds == 7200
    assert settings.openai_api_key == "openai-key"
    assert settings.gemini_api_key == "gemini-key"
    assert settings.claude_api_key == "claude-key"


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


# ---------- load_trading_config ----------


def test_load_trading_config_returns_dict(tmp_path: Path) -> None:
    yaml_file = tmp_path / "trading.yaml"
    yaml_file.write_text("min_order_usdc: 10.0\n", encoding="utf-8")

    result = load_trading_config(yaml_file)

    assert result == {"min_order_usdc": 10.0}


def test_load_trading_config_raises_if_file_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_trading_config(tmp_path / "non_esistente.yaml")


# ---------- load_symbol_config ----------


def test_load_symbol_config_returns_symbol(tmp_path: Path) -> None:
    yaml_file = tmp_path / "symbols.yaml"
    yaml_file.write_text("symbol: BTCUSDC\n", encoding="utf-8")

    result = load_symbol_config(yaml_file)

    assert result == "BTCUSDC"


def test_load_symbol_config_raises_if_symbol_missing(tmp_path: Path) -> None:
    yaml_file = tmp_path / "symbols.yaml"
    yaml_file.write_text("altro_campo: qualcosa\n", encoding="utf-8")

    with pytest.raises(ValueError, match="symbol"):
        load_symbol_config(yaml_file)


def test_load_symbol_config_raises_if_file_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_symbol_config(tmp_path / "non_esistente.yaml")


# ---------- load_llm_model_config ----------


def test_load_llm_model_config_returns_dict(tmp_path: Path) -> None:
    yaml_file = tmp_path / "model.yaml"
    yaml_file.write_text(
        "provider: openai\nmodel: gpt-5.4\ntemperature: 0.2\nmax_tokens: 512\n",
        encoding="utf-8",
    )

    result = load_llm_model_config(yaml_file)

    assert result["provider"] == "openai"
    assert result["model"] == "gpt-5.4"
    assert result["temperature"] == pytest.approx(0.2)
    assert result["max_tokens"] == 512


def test_load_llm_model_config_raises_if_file_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_llm_model_config(tmp_path / "non_esistente.yaml")

