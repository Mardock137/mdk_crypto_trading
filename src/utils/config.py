from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

import yaml
from dotenv import load_dotenv

from src.core.contracts import InvestmentMandate


class TradingMode(str, Enum):
    DEMO = "DEMO"
    REAL = "REAL"


@dataclass(frozen=True, slots=True)
class AppSettings:
    trading_mode: TradingMode
    kill_switch: bool
    cycle_interval_seconds: int
    openai_api_key: str | None
    gemini_api_key: str | None
    claude_api_key: str | None
    binance_api_key: str | None
    binance_secret_key: str | None
    binance_demo_api_key: str | None
    binance_demo_secret_key: str | None
    binance_demo_base_url: str | None
    log_level: str
    telegram_bot_token: str | None
    telegram_chat_id: str | None


def load_settings(
    env: Mapping[str, str] | None = None,
    env_path: str | Path | None = None,
) -> AppSettings:
    if env is None:
        if env_path is not None:
            load_dotenv(Path(env_path))
        else:
            load_dotenv()
        env = os.environ

    trading_mode = TradingMode(_require_value(env, "TRADING_MODE"))
    cycle_interval_seconds = int(_require_value(env, "CYCLE_INTERVAL_SECONDS"))
    kill_switch = _read_bool(env.get("KILL_SWITCH", "1"))

    return AppSettings(
        trading_mode=trading_mode,
        kill_switch=kill_switch,
        cycle_interval_seconds=cycle_interval_seconds,
        openai_api_key=env.get("OPENAI_API_KEY"),
        gemini_api_key=env.get("GEMINI_API_KEY"),
        claude_api_key=env.get("CLAUDE_API_KEY"),
        binance_api_key=env.get("BINANCE_API_KEY"),
        binance_secret_key=env.get("BINANCE_SECRET_KEY"),
        binance_demo_api_key=env.get("BINANCE_DEMO_API_KEY"),
        binance_demo_secret_key=env.get("BINANCE_DEMO_SECRET_KEY"),
        binance_demo_base_url=env.get("BINANCE_DEMO_BASE_URL"),
        log_level=env.get("LOG_LEVEL", "INFO"),
        telegram_bot_token=env.get("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=env.get("TELEGRAM_CHAT_ID"),
    )


def _load_yaml(path: str | Path) -> dict[str, Any]:
    """Carica e ritorna il contenuto di un file YAML."""
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"File di configurazione non trovato: {resolved}")
    with open(resolved, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_trading_config(
    config_path: str | Path = "config/trading.yaml",
) -> dict[str, Any]:
    """Carica le regole operative dal file YAML di configurazione."""
    return _load_yaml(config_path)


def load_mandate(trading_config: Mapping[str, Any]) -> InvestmentMandate:
    """Estrae e valida la sezione `mandate` dal dict di trading.yaml."""
    raw = trading_config.get("mandate")
    if not isinstance(raw, Mapping):
        raise ValueError(
            "Sezione 'mandate' mancante o non valida in trading.yaml"
        )

    required = (
        "objective",
        "min_monthly_return_pct",
        "max_drawdown_pct",
        "horizon",
        "max_position_pct",
        "min_trades_per_week",
    )
    missing = [k for k in required if k not in raw]
    if missing:
        raise ValueError(
            f"Campi mancanti nella sezione 'mandate' di trading.yaml: {missing}"
        )

    return InvestmentMandate(
        objective=str(raw["objective"]),
        min_monthly_return_pct=float(raw["min_monthly_return_pct"]),
        max_drawdown_pct=float(raw["max_drawdown_pct"]),
        horizon=str(raw["horizon"]),
        max_position_pct=float(raw["max_position_pct"]),
        min_trades_per_week=int(raw["min_trades_per_week"]),
    )


def load_symbol_config(
    config_path: str | Path = "config/symbols.yaml",
) -> dict[str, str]:
    """Carica il simbolo di trading e la quote currency dal file YAML."""
    data = _load_yaml(config_path)
    symbol = data.get("symbol")
    quote_currency = data.get("quote_currency")
    if not symbol:
        raise ValueError("Campo 'symbol' mancante in symbols.yaml")
    if not quote_currency:
        raise ValueError("Campo 'quote_currency' mancante in symbols.yaml")
    return {"symbol": str(symbol), "quote_currency": str(quote_currency)}


def load_llm_model_config(
    config_path: str | Path,
) -> dict[str, Any]:
    """Carica la configurazione di un modello LLM dal file YAML."""
    return _load_yaml(config_path)


def _require_value(env: Mapping[str, str], key: str) -> str:
    value = env.get(key)
    if value is None or value == "":
        raise ValueError(f"Missing required environment variable: {key}")
    return value


def _read_bool(raw_value: str) -> bool:
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {raw_value}")

