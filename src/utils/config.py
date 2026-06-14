from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

import yaml
from dotenv import load_dotenv

from src.core.contracts import CycleSkipConfig, InvestmentMandate

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_DEFAULT_CYCLE_SKIP_CONFIG = CycleSkipConfig(
    enabled=False,
    max_consecutive_skips=5,
    price_delta_pct=0.5,
    rsi_delta=2.0,
    macd_sign_must_match=True,
    require_no_order_events=True,
    require_previous_action_hold=True,
)


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
    alpha_vantage_api_key: str | None


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
        alpha_vantage_api_key=env.get("ALPHA_VANTAGE_API_KEY"),
    )


def _load_yaml(path: str | Path) -> dict[str, Any]:
    """Carica e ritorna il contenuto di un file YAML."""
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"File di configurazione non trovato: {resolved}")
    with open(resolved, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_trading_config(
    config_path: str | Path = _PROJECT_ROOT / "config/trading.yaml",
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
        "max_drawdown_pct",
        "horizon",
        "max_position_pct",
    )
    missing = [k for k in required if k not in raw]
    if missing:
        raise ValueError(
            f"Campi mancanti nella sezione 'mandate' di trading.yaml: {missing}"
        )

    return InvestmentMandate(
        max_drawdown_pct=float(raw["max_drawdown_pct"]),
        horizon=str(raw["horizon"]),
        max_position_pct=float(raw["max_position_pct"]),
    )


def load_symbol_config(
    config_path: str | Path = _PROJECT_ROOT / "config/symbols.yaml",
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


def load_cycle_skip_config(
    config_path: str | Path = _PROJECT_ROOT / "config/cycle_skip.yaml",
) -> CycleSkipConfig:
    """Carica la configurazione del pre-check di skip ciclo dal file YAML.

    Fallback safe: se il file non esiste, ritorna una configurazione con
    ``enabled=False`` (nessun ciclo viene saltato).
    """
    resolved = Path(config_path)
    if not resolved.exists():
        return _DEFAULT_CYCLE_SKIP_CONFIG

    data = _load_yaml(resolved)
    thresholds = data.get("thresholds")
    if not isinstance(thresholds, Mapping):
        raise ValueError(
            "Sezione 'thresholds' mancante o non valida in cycle_skip.yaml"
        )

    required_top = ("enabled", "max_consecutive_skips")
    missing_top = [k for k in required_top if k not in data]
    if missing_top:
        raise ValueError(
            f"Campi mancanti in cycle_skip.yaml: {missing_top}"
        )

    required_thresholds = (
        "price_delta_pct",
        "rsi_delta",
        "macd_sign_must_match",
        "require_no_order_events",
        "require_previous_action_hold",
    )
    missing_thresholds = [k for k in required_thresholds if k not in thresholds]
    if missing_thresholds:
        raise ValueError(
            f"Campi mancanti in 'thresholds' di cycle_skip.yaml: {missing_thresholds}"
        )

    return CycleSkipConfig(
        enabled=bool(data["enabled"]),
        max_consecutive_skips=int(data["max_consecutive_skips"]),
        price_delta_pct=float(thresholds["price_delta_pct"]),
        rsi_delta=float(thresholds["rsi_delta"]),
        macd_sign_must_match=bool(thresholds["macd_sign_must_match"]),
        require_no_order_events=bool(thresholds["require_no_order_events"]),
        require_previous_action_hold=bool(thresholds["require_previous_action_hold"]),
    )


def load_llm_model_config(
    config_path: str | Path,
) -> dict[str, Any]:
    """Carica la configurazione di un modello LLM dal file YAML."""
    return _load_yaml(config_path)


def load_news_config(
    config_path: str | Path = _PROJECT_ROOT / "config/news.yaml",
) -> dict[str, Any]:
    """Carica la configurazione della fonte news dal file YAML.

    Fallback safe: se il file non esiste, ritorna un dict vuoto senza errori.
    """
    resolved = Path(config_path)
    if not resolved.exists():
        return {}
    return _load_yaml(resolved)


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

