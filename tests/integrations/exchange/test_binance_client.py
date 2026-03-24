from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.integrations.exchange.binance_client import BinanceClient
from src.utils.config import AppSettings, TradingMode


def _make_settings(**overrides: Any) -> AppSettings:
    """Helper per creare AppSettings con valori di default ragionevoli."""
    defaults: dict[str, Any] = {
        "trading_mode": TradingMode.DEMO,
        "kill_switch": True,
        "cycle_interval_seconds": 60,
        "openai_api_key": None,
        "gemini_api_key": None,
        "binance_api_key": None,
        "binance_secret_key": None,
        "binance_demo_api_key": "demo-key",
        "binance_demo_secret_key": "demo-secret",
        "binance_demo_base_url": "https://demo-api.binance.com/api",
    }
    defaults.update(overrides)
    return AppSettings(**defaults)


# ---------- Verifica credenziali DEMO ----------


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_demo_mode_uses_demo_credentials(mock_client_cls: MagicMock) -> None:
    """In modalità DEMO devono essere usate le credenziali demo e l'URL demo."""
    settings = _make_settings(trading_mode=TradingMode.DEMO)
    BinanceClient(settings)

    mock_client_cls.assert_called_once_with(
        api_key="demo-key",
        api_secret="demo-secret",
    )
    assert mock_client_cls.return_value.API_URL == "https://demo-api.binance.com/api"


# ---------- Verifica credenziali REAL ----------


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_real_mode_uses_real_credentials(mock_client_cls: MagicMock) -> None:
    """In modalità REAL devono essere usate le credenziali reali senza testnet."""
    settings = _make_settings(
        trading_mode=TradingMode.REAL,
        binance_api_key="real-key",
        binance_secret_key="real-secret",
    )
    BinanceClient(settings)

    mock_client_cls.assert_called_once_with(
        api_key="real-key",
        api_secret="real-secret",
    )


# ---------- Verifica ValueError per credenziali mancanti ----------


def test_demo_mode_raises_if_credentials_missing() -> None:
    """Modalità DEMO senza credenziali demo deve lanciare ValueError."""
    settings = _make_settings(
        trading_mode=TradingMode.DEMO,
        binance_demo_api_key=None,
        binance_demo_secret_key=None,
    )
    with pytest.raises(ValueError, match="DEMO"):
        BinanceClient(settings)


def test_demo_mode_raises_if_base_url_missing() -> None:
    """Modalità DEMO senza binance_demo_base_url deve lanciare ValueError."""
    settings = _make_settings(
        trading_mode=TradingMode.DEMO,
        binance_demo_base_url=None,
    )
    with pytest.raises(ValueError, match="DEMO"):
        BinanceClient(settings)


def test_real_mode_raises_if_credentials_missing() -> None:
    """Modalità REAL senza credenziali reali deve lanciare ValueError."""
    settings = _make_settings(
        trading_mode=TradingMode.REAL,
        binance_api_key=None,
        binance_secret_key=None,
    )
    with pytest.raises(ValueError, match="REAL"):
        BinanceClient(settings)


# ---------- Verifica metodi ping e get_account_info ----------


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_ping_calls_sdk_ping(mock_client_cls: MagicMock) -> None:
    """ping() deve chiamare il metodo ping dell'SDK Binance."""
    mock_instance = mock_client_cls.return_value
    mock_instance.ping.return_value = {}

    client = BinanceClient(_make_settings())
    result = client.ping()

    mock_instance.ping.assert_called_once()
    assert result is True


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_get_account_info_calls_sdk_get_account(mock_client_cls: MagicMock) -> None:
    """get_account_info() deve chiamare get_account dell'SDK Binance."""
    mock_instance = mock_client_cls.return_value
    mock_instance.get_account.return_value = {"balances": []}

    client = BinanceClient(_make_settings())
    result = client.get_account_info()

    mock_instance.get_account.assert_called_once()
    assert result == {"balances": []}
