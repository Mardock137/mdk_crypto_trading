from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

import yaml
from dotenv import load_dotenv


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
    binance_api_key: str | None
    binance_secret_key: str | None
    binance_demo_api_key: str | None
    binance_demo_secret_key: str | None
    binance_demo_base_url: str | None
    log_level: str


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
        binance_api_key=env.get("BINANCE_API_KEY"),
        binance_secret_key=env.get("BINANCE_SECRET_KEY"),
        binance_demo_api_key=env.get("BINANCE_DEMO_API_KEY"),
        binance_demo_secret_key=env.get("BINANCE_DEMO_SECRET_KEY"),
        binance_demo_base_url=env.get("BINANCE_DEMO_BASE_URL"),
        log_level=env.get("LOG_LEVEL", "INFO"),
    )


def load_trading_config(
    config_path: str | Path = "config/trading.yaml",
) -> dict[str, Any]:
    """Carica le regole operative dal file YAML di configurazione."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"File di configurazione non trovato: {path}")
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}
    return data


def load_symbol_config(
    config_path: str | Path = "config/symbols.yaml",
) -> str:
    """Carica il simbolo di trading dal file YAML di configurazione."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"File di configurazione non trovato: {path}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    symbol = data.get("symbol")
    if not symbol:
        raise ValueError("Campo 'symbol' mancante in symbols.yaml")
    return str(symbol)


def load_llm_model_config(
    config_path: str | Path,
) -> dict[str, Any]:
    """Carica la configurazione di un modello LLM dal file YAML."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"File di configurazione non trovato: {path}")
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}
    return data


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

