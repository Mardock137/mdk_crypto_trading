from pathlib import Path

import pytest

from src.utils.config import (
    TradingMode,
    load_cycle_skip_config,
    load_llm_model_config,
    load_mandate,
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
            "TELEGRAM_BOT_TOKEN": "tg-token",
            "TELEGRAM_CHAT_ID": "tg-chat",
        }
    )

    assert settings.trading_mode is TradingMode.DEMO
    assert settings.kill_switch is True
    assert settings.cycle_interval_seconds == 7200
    assert settings.openai_api_key == "openai-key"
    assert settings.gemini_api_key == "gemini-key"
    assert settings.claude_api_key == "claude-key"
    assert settings.telegram_bot_token == "tg-token"
    assert settings.telegram_chat_id == "tg-chat"


def test_load_settings_telegram_defaults_to_none() -> None:
    """Se le variabili Telegram non sono presenti, devono essere None."""
    settings = load_settings(
        {
            "TRADING_MODE": "DEMO",
            "CYCLE_INTERVAL_SECONDS": "7200",
        }
    )

    assert settings.telegram_bot_token is None
    assert settings.telegram_chat_id is None


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


def test_load_symbol_config_returns_dict(tmp_path: Path) -> None:
    yaml_file = tmp_path / "symbols.yaml"
    yaml_file.write_text("symbol: BTCUSDC\nquote_currency: USDC\n", encoding="utf-8")

    result = load_symbol_config(yaml_file)

    assert result == {"symbol": "BTCUSDC", "quote_currency": "USDC"}


def test_load_symbol_config_raises_if_symbol_missing(tmp_path: Path) -> None:
    yaml_file = tmp_path / "symbols.yaml"
    yaml_file.write_text("quote_currency: USDC\n", encoding="utf-8")

    with pytest.raises(ValueError, match="symbol"):
        load_symbol_config(yaml_file)


def test_load_symbol_config_raises_if_quote_currency_missing(tmp_path: Path) -> None:
    yaml_file = tmp_path / "symbols.yaml"
    yaml_file.write_text("symbol: BTCUSDC\n", encoding="utf-8")

    with pytest.raises(ValueError, match="quote_currency"):
        load_symbol_config(yaml_file)


def test_load_symbol_config_raises_if_file_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_symbol_config(tmp_path / "non_esistente.yaml")


# ---------- load_mandate ----------


def _valid_mandate_dict() -> dict:
    return {
        "max_drawdown_pct": 15.0,
        "horizon": "Intraday to swing",
        "max_position_pct": 70.0,
    }


def test_load_mandate_returns_investment_mandate() -> None:
    config = {"min_order_usdc": 10.0, "mandate": _valid_mandate_dict()}

    mandate = load_mandate(config)

    assert mandate.max_drawdown_pct == pytest.approx(15.0)
    assert mandate.horizon == "Intraday to swing"
    assert mandate.max_position_pct == pytest.approx(70.0)


def test_load_mandate_raises_if_section_missing() -> None:
    with pytest.raises(ValueError, match="mandate"):
        load_mandate({"min_order_usdc": 10.0})


def test_load_mandate_raises_if_field_missing() -> None:
    partial = _valid_mandate_dict()
    del partial["horizon"]

    with pytest.raises(ValueError, match="horizon"):
        load_mandate({"mandate": partial})


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


# ---------- load_cycle_skip_config ----------


_VALID_CYCLE_SKIP_YAML = """\
enabled: true
max_consecutive_skips: 5
thresholds:
  price_delta_pct: 0.5
  rsi_delta: 2.0
  macd_sign_must_match: true
  require_no_order_events: true
  require_previous_action_hold: true
"""


def test_load_cycle_skip_config_returns_expected_values(tmp_path: Path) -> None:
    yaml_file = tmp_path / "cycle_skip.yaml"
    yaml_file.write_text(_VALID_CYCLE_SKIP_YAML, encoding="utf-8")

    config = load_cycle_skip_config(yaml_file)

    assert config.enabled is True
    assert config.max_consecutive_skips == 5
    assert config.price_delta_pct == pytest.approx(0.5)
    assert config.rsi_delta == pytest.approx(2.0)
    assert config.macd_sign_must_match is True
    assert config.require_no_order_events is True
    assert config.require_previous_action_hold is True


def test_load_cycle_skip_config_fallback_when_file_missing(tmp_path: Path) -> None:
    config = load_cycle_skip_config(tmp_path / "missing.yaml")

    assert config.enabled is False
    assert config.max_consecutive_skips == 5


def test_load_cycle_skip_config_raises_if_thresholds_missing(tmp_path: Path) -> None:
    yaml_file = tmp_path / "cycle_skip.yaml"
    yaml_file.write_text("enabled: true\nmax_consecutive_skips: 5\n", encoding="utf-8")

    with pytest.raises(ValueError, match="thresholds"):
        load_cycle_skip_config(yaml_file)


def test_load_cycle_skip_config_raises_if_field_missing(tmp_path: Path) -> None:
    yaml_file = tmp_path / "cycle_skip.yaml"
    yaml_file.write_text(
        "max_consecutive_skips: 5\n"
        "thresholds:\n"
        "  price_delta_pct: 0.5\n"
        "  rsi_delta: 2.0\n"
        "  macd_sign_must_match: true\n"
        "  require_no_order_events: true\n"
        "  require_previous_action_hold: true\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="enabled"):
        load_cycle_skip_config(yaml_file)


def test_load_cycle_skip_config_raises_if_threshold_field_missing(tmp_path: Path) -> None:
    yaml_file = tmp_path / "cycle_skip.yaml"
    yaml_file.write_text(
        "enabled: true\n"
        "max_consecutive_skips: 5\n"
        "thresholds:\n"
        "  price_delta_pct: 0.5\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rsi_delta"):
        load_cycle_skip_config(yaml_file)

