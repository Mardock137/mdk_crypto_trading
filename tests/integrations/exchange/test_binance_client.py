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
        "claude_api_key": None,
        "binance_api_key": None,
        "binance_secret_key": None,
        "binance_demo_api_key": "demo-key",
        "binance_demo_secret_key": "demo-secret",
        "binance_demo_base_url": "https://demo-api.binance.com/api",
        "log_level": "INFO",
        "telegram_bot_token": None,
        "telegram_chat_id": None,
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


# ---------- Verifica get_market_snapshot ----------


def _setup_market_mocks(mock_instance: MagicMock) -> None:
    """Configura i mock per tutte le chiamate usate da get_market_snapshot."""
    mock_instance.get_symbol_ticker.return_value = {"price": "50000.0"}
    mock_instance.get_avg_price.return_value = {"price": "49950.0"}
    mock_instance.get_ticker.return_value = {"volume": "1234.5"}
    mock_instance.get_order_book.return_value = {
        "bids": [["49999", "0.1"]],
        "asks": [["50001", "0.2"]],
    }
    # Klines: lista di liste (formato Binance); indice 4 = close
    fake_kline = [0, "50000", "50100", "49900", "50050", "100", 0, 0, 0, 0, 0, 0]
    mock_instance.get_klines.return_value = [fake_kline] * 60


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_get_market_snapshot_returns_populated_snapshot(
    mock_client_cls: MagicMock,
) -> None:
    """get_market_snapshot deve restituire un MarketDataSnapshot con i campi popolati."""
    mock_instance = mock_client_cls.return_value
    _setup_market_mocks(mock_instance)

    client = BinanceClient(_make_settings())
    snapshot = client.get_market_snapshot("BTCUSDC")

    assert snapshot.symbol == "BTCUSDC"
    assert snapshot.price == 50000.0
    assert snapshot.avg_price == 49950.0
    assert snapshot.volume_24h == 1234.5
    assert len(snapshot.order_book_top_10_bids) == 1
    assert "rsi_14" in snapshot.indicators


# ---------- Verifica get_portfolio_state ----------


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_get_portfolio_state_returns_populated_state(
    mock_client_cls: MagicMock,
) -> None:
    """get_portfolio_state deve restituire un PortfolioState con i campi popolati."""
    mock_instance = mock_client_cls.return_value
    mock_instance.get_account.return_value = {
        "balances": [
            {"asset": "USDC", "free": "500.0", "locked": "100.0"},
            {"asset": "BTC", "free": "0.01", "locked": "0.0"},
        ],
    }
    mock_instance.get_symbol_ticker.return_value = {"price": "50000.0"}
    mock_instance.get_open_orders.return_value = []
    mock_instance.get_my_trades.return_value = [{"id": 1}]

    client = BinanceClient(_make_settings())
    state = client.get_portfolio_state("BTCUSDC")

    assert state.usdc_balance == 500.0
    assert state.usdc_balance_total == 600.0
    assert state.portfolio_qty_free == 0.01
    assert state.portfolio_qty_total == 0.01
    assert state.usdc_value == 0.01 * 50000.0
    assert state.last_trades == [{"id": 1}]


# ---------- Verifica metodi ordini ----------


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_market_order_buy(mock_client_cls: MagicMock) -> None:
    """place_market_order con side BUY chiama order_market_buy."""
    mock_instance = mock_client_cls.return_value
    mock_instance.order_market_buy.return_value = {"orderId": "100"}

    client = BinanceClient(_make_settings())
    result = client.place_market_order("BTCUSDC", "BUY", 0.001)

    mock_instance.order_market_buy.assert_called_once_with(
        symbol="BTCUSDC", quantity=0.001,
    )
    assert result == {"orderId": "100"}


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_market_order_sell(mock_client_cls: MagicMock) -> None:
    """place_market_order con side SELL chiama order_market_sell."""
    mock_instance = mock_client_cls.return_value
    mock_instance.order_market_sell.return_value = {"orderId": "101"}

    client = BinanceClient(_make_settings())
    result = client.place_market_order("BTCUSDC", "SELL", 0.001)

    mock_instance.order_market_sell.assert_called_once_with(
        symbol="BTCUSDC", quantity=0.001,
    )
    assert result == {"orderId": "101"}


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_limit_order_buy(mock_client_cls: MagicMock) -> None:
    """place_limit_order con side BUY chiama order_limit_buy con timeInForce GTC."""
    mock_instance = mock_client_cls.return_value
    mock_instance.order_limit_buy.return_value = {"orderId": "200"}

    client = BinanceClient(_make_settings())
    result = client.place_limit_order("BTCUSDC", "BUY", 0.001, 97000.0)

    mock_instance.order_limit_buy.assert_called_once_with(
        symbol="BTCUSDC", quantity=0.001, price="97000.0", timeInForce="GTC",
    )
    assert result == {"orderId": "200"}


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_limit_order_sell(mock_client_cls: MagicMock) -> None:
    """place_limit_order con side SELL chiama order_limit_sell con timeInForce GTC."""
    mock_instance = mock_client_cls.return_value
    mock_instance.order_limit_sell.return_value = {"orderId": "201"}

    client = BinanceClient(_make_settings())
    result = client.place_limit_order("BTCUSDC", "SELL", 0.001, 99000.0)

    mock_instance.order_limit_sell.assert_called_once_with(
        symbol="BTCUSDC", quantity=0.001, price="99000.0", timeInForce="GTC",
    )
    assert result == {"orderId": "201"}


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_cancel_order(mock_client_cls: MagicMock) -> None:
    """cancel_order chiama cancel_order dell'SDK con orderId."""
    mock_instance = mock_client_cls.return_value
    mock_instance.cancel_order.return_value = {"status": "CANCELED"}

    client = BinanceClient(_make_settings())
    result = client.cancel_order("BTCUSDC", "12345")

    mock_instance.cancel_order.assert_called_once_with(
        symbol="BTCUSDC", orderId="12345",
    )
    assert result == {"status": "CANCELED"}
