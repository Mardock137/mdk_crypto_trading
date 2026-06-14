from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from binance.exceptions import BinanceAPIException, BinanceRequestException

from src.core.exceptions import ExchangeError
from src.integrations.exchange.binance_client import BinanceClient, _add_age_to_orders
from src.utils.config import AppSettings, TradingMode


def _setup_symbol_info(
    mock_instance: MagicMock,
    *,
    step_size: str = "0.00001",
    min_qty: str = "0.00001",
    tick_size: str = "0.01",
    min_notional: str = "10.0",
) -> None:
    """Configura il mock di get_symbol_info con filtri standard."""
    mock_instance.get_symbol_info.return_value = {
        "symbol": "BTCUSDC",
        "filters": [
            {"filterType": "LOT_SIZE", "stepSize": step_size, "minQty": min_qty},
            {"filterType": "PRICE_FILTER", "tickSize": tick_size},
            {"filterType": "NOTIONAL", "minNotional": min_notional},
        ],
    }


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
        "alpha_vantage_api_key": None,
    }
    defaults.update(overrides)
    return AppSettings(**defaults)


def _assert_valid_uuid4(value: str) -> None:
    """Verifica che il valore sia uno UUID v4 serializzato come stringa standard."""
    parsed = UUID(value)
    assert len(value) == 36
    assert str(parsed) == value
    assert parsed.version == 4


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
def test_ping_returns_false_on_exception(mock_client_cls: MagicMock) -> None:
    """ping() deve ritornare False se l'SDK lancia un'eccezione."""
    mock_instance = mock_client_cls.return_value
    mock_instance.ping.side_effect = RuntimeError("Network error")

    client = BinanceClient(_make_settings())
    result = client.ping()

    assert result is False


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
    assert "rsi" in snapshot.indicators
    assert "rsi_prev" in snapshot.indicators
    assert "rsi_14" not in snapshot.indicators


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_get_market_snapshot_logs_warning_when_rsi_missing_but_macd_available(
    mock_client_cls: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_instance = mock_client_cls.return_value
    _setup_market_mocks(mock_instance)

    client = BinanceClient(_make_settings())
    with (
        patch(
            "src.integrations.exchange.binance_client.indicators.compute_indicators_bundle",
            return_value={"rsi": None, "macd": -1.0, "macd_signal": -2.0},
        ),
        caplog.at_level(logging.WARNING),
    ):
        snapshot = client.get_market_snapshot("BTCUSDC")

    assert snapshot.indicators["rsi"] is None
    assert "RSI unavailable while MACD is available" in caplog.text


# ---------- Verifica retry su get_market_snapshot ----------


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_get_market_snapshot_retries_on_request_exception(
    mock_client_cls: MagicMock,
) -> None:
    """get_market_snapshot deve ritentare su BinanceRequestException."""
    mock_instance = mock_client_cls.return_value
    _setup_market_mocks(mock_instance)
    mock_instance.get_symbol_ticker.side_effect = [
        BinanceRequestException("Connection error"),
        {"price": "50000.0"},
    ]

    client = BinanceClient(_make_settings())
    snapshot = client.get_market_snapshot("BTCUSDC")

    assert snapshot.symbol == "BTCUSDC"
    assert mock_instance.get_symbol_ticker.call_count == 2


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_get_market_snapshot_no_retry_on_client_error(
    mock_client_cls: MagicMock,
) -> None:
    """get_market_snapshot NON deve ritentare su errori 400 (client error) e rilancia ExchangeError."""
    mock_instance = mock_client_cls.return_value
    _setup_market_mocks(mock_instance)
    api_exc = BinanceAPIException(
        response=MagicMock(status_code=400, text="Bad Request"),
        status_code=400,
        text="Bad Request",
    )
    mock_instance.get_symbol_ticker.side_effect = api_exc

    client = BinanceClient(_make_settings())
    with pytest.raises(ExchangeError):
        client.get_market_snapshot("BTCUSDC")

    assert mock_instance.get_symbol_ticker.call_count == 1


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_get_market_snapshot_raises_exchange_error_after_all_retries(
    mock_client_cls: MagicMock,
) -> None:
    """get_market_snapshot deve sollevare ExchangeError dopo aver esaurito i retry."""
    mock_instance = mock_client_cls.return_value
    _setup_market_mocks(mock_instance)
    mock_instance.get_symbol_ticker.side_effect = BinanceRequestException("Network error")

    client = BinanceClient(_make_settings())
    with pytest.raises(ExchangeError):
        client.get_market_snapshot("BTCUSDC")


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_get_portfolio_state_raises_exchange_error_on_binance_exception(
    mock_client_cls: MagicMock,
) -> None:
    """get_portfolio_state deve sollevare ExchangeError su errori Binance."""
    mock_instance = mock_client_cls.return_value
    api_exc = BinanceAPIException(
        response=MagicMock(status_code=500, text="Internal Server Error"),
        status_code=500,
        text="Internal Server Error",
    )
    mock_instance.get_account.side_effect = api_exc

    client = BinanceClient(_make_settings())
    with pytest.raises(ExchangeError):
        client.get_portfolio_state("BTCUSDC")


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


# ---------- Verifica _add_age_to_orders ----------


def test_add_age_to_orders_adds_age_hours() -> None:
    """_add_age_to_orders aggiunge age_hours basandosi sul campo time."""
    import time as _time

    now_ms = int(_time.time() * 1000)
    two_hours_ago_ms = now_ms - 2 * 3_600_000

    orders = [{"orderId": 1, "time": two_hours_ago_ms}]
    _add_age_to_orders(orders)

    assert orders[0]["age_hours"] == pytest.approx(2.0, abs=0.1)


def test_add_age_to_orders_skips_orders_without_time() -> None:
    """Ordini privi del campo time vengono ignorati silenziosamente."""
    orders = [{"orderId": 1}]
    _add_age_to_orders(orders)
    assert "age_hours" not in orders[0]


def test_add_age_to_orders_skips_invalid_timestamp() -> None:
    """Ordini con timestamp non numerico vengono ignorati senza errore."""
    orders = [{"orderId": 1, "time": "not-a-number"}]
    _add_age_to_orders(orders)
    assert "age_hours" not in orders[0]


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_get_portfolio_state_adds_age_hours_to_open_orders(
    mock_client_cls: MagicMock,
) -> None:
    """get_portfolio_state arricchisce gli ordini aperti con age_hours."""
    import time as _time

    now_ms = int(_time.time() * 1000)
    one_hour_ago_ms = now_ms - 1 * 3_600_000

    mock_instance = mock_client_cls.return_value
    mock_instance.get_account.return_value = {
        "balances": [{"asset": "USDC", "free": "100.0", "locked": "0.0"}],
    }
    mock_instance.get_symbol_ticker.return_value = {"price": "50000.0"}
    mock_instance.get_open_orders.return_value = [
        {"orderId": 7, "time": one_hour_ago_ms, "side": "BUY"},
    ]
    mock_instance.get_my_trades.return_value = []

    client = BinanceClient(_make_settings())
    state = client.get_portfolio_state("BTCUSDC")

    assert len(state.open_orders) == 1
    assert state.open_orders[0]["age_hours"] == pytest.approx(1.0, abs=0.1)


# ---------- Verifica fetch OHLC + ATR ----------


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_get_market_snapshot_passes_ohlc_to_indicators(
    mock_client_cls: MagicMock,
) -> None:
    """get_market_snapshot deve fetchare highs/lows/closes 1h e passarli al bundle."""
    mock_instance = mock_client_cls.return_value
    _setup_market_mocks(mock_instance)

    client = BinanceClient(_make_settings())
    with patch(
        "src.integrations.exchange.binance_client.indicators.compute_indicators_bundle",
        return_value={"rsi": 50.0, "atr": 100.0, "atr_prev": 95.0},
    ) as mock_bundle:
        client.get_market_snapshot("BTCUSDC")

    args, kwargs = mock_bundle.call_args
    # closes passati come primo positional, highs/lows come kwargs
    assert len(args[0]) == 60
    assert "highs" in kwargs and "lows" in kwargs
    assert len(kwargs["highs"]) == 60
    assert len(kwargs["lows"]) == 60


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_get_market_snapshot_indicators_include_atr(
    mock_client_cls: MagicMock,
) -> None:
    """Lo snapshot prodotto deve contenere atr e atr_prev tra gli indicatori."""
    mock_instance = mock_client_cls.return_value
    _setup_market_mocks(mock_instance)

    client = BinanceClient(_make_settings())
    snapshot = client.get_market_snapshot("BTCUSDC")

    assert "atr" in snapshot.indicators
    assert "atr_prev" in snapshot.indicators


# ---------- Verifica nuovi limiti candele 4h e 1d ----------


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_fetch_candles_uses_updated_limits_for_4h_and_1d(
    mock_client_cls: MagicMock,
) -> None:
    """_fetch_candles deve richiedere 50 candele 4h e 30 candele 1d."""
    mock_instance = mock_client_cls.return_value
    _setup_market_mocks(mock_instance)

    client = BinanceClient(_make_settings())
    client.get_market_snapshot("BTCUSDC")

    # Estrae le coppie (interval, limit) da tutte le chiamate get_klines
    calls = [
        (call.kwargs.get("interval"), call.kwargs.get("limit"))
        for call in mock_instance.get_klines.call_args_list
    ]
    assert ("4h", 50) in calls
    assert ("1d", 30) in calls


# ---------- Verifica metodi ordini ----------


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_market_order_buy(mock_client_cls: MagicMock) -> None:
    """place_market_order con side BUY chiama order_market_buy."""
    mock_instance = mock_client_cls.return_value
    _setup_symbol_info(mock_instance)
    mock_instance.get_symbol_ticker.return_value = {"price": "50000.0"}
    mock_instance.order_market_buy.return_value = {"orderId": "100"}

    client = BinanceClient(_make_settings())
    result = client.place_market_order("BTCUSDC", "BUY", 0.001)

    mock_instance.order_market_buy.assert_called_once()
    _, kwargs = mock_instance.order_market_buy.call_args
    assert kwargs["symbol"] == "BTCUSDC"
    assert kwargs["quantity"] == Decimal("0.00100")
    _assert_valid_uuid4(kwargs["newClientOrderId"])
    assert result == {"orderId": "100"}


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_market_order_sell(mock_client_cls: MagicMock) -> None:
    """place_market_order con side SELL chiama order_market_sell."""
    mock_instance = mock_client_cls.return_value
    _setup_symbol_info(mock_instance)
    mock_instance.get_symbol_ticker.return_value = {"price": "50000.0"}
    mock_instance.order_market_sell.return_value = {"orderId": "101"}

    client = BinanceClient(_make_settings())
    result = client.place_market_order("BTCUSDC", "SELL", 0.001)

    mock_instance.order_market_sell.assert_called_once()
    _, kwargs = mock_instance.order_market_sell.call_args
    assert kwargs["symbol"] == "BTCUSDC"
    assert kwargs["quantity"] == Decimal("0.00100")
    _assert_valid_uuid4(kwargs["newClientOrderId"])
    assert result == {"orderId": "101"}


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_limit_order_buy(mock_client_cls: MagicMock) -> None:
    """place_limit_order con side BUY chiama order_limit_buy con timeInForce GTC."""
    mock_instance = mock_client_cls.return_value
    _setup_symbol_info(mock_instance)
    mock_instance.order_limit_buy.return_value = {"orderId": "200"}

    client = BinanceClient(_make_settings())
    result = client.place_limit_order("BTCUSDC", "BUY", 0.001, 97000.0)

    mock_instance.order_limit_buy.assert_called_once()
    _, kwargs = mock_instance.order_limit_buy.call_args
    assert kwargs["symbol"] == "BTCUSDC"
    assert kwargs["quantity"] == Decimal("0.00100")
    assert kwargs["price"] == "97000.00"
    assert kwargs["timeInForce"] == "GTC"
    _assert_valid_uuid4(kwargs["newClientOrderId"])
    assert result == {"orderId": "200"}


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_limit_order_sell(mock_client_cls: MagicMock) -> None:
    """place_limit_order con side SELL chiama order_limit_sell con timeInForce GTC."""
    mock_instance = mock_client_cls.return_value
    _setup_symbol_info(mock_instance)
    mock_instance.order_limit_sell.return_value = {"orderId": "201"}

    client = BinanceClient(_make_settings())
    result = client.place_limit_order("BTCUSDC", "SELL", 0.001, 99000.0)

    mock_instance.order_limit_sell.assert_called_once()
    _, kwargs = mock_instance.order_limit_sell.call_args
    assert kwargs["symbol"] == "BTCUSDC"
    assert kwargs["quantity"] == Decimal("0.00100")
    assert kwargs["price"] == "99000.00"
    assert kwargs["timeInForce"] == "GTC"
    _assert_valid_uuid4(kwargs["newClientOrderId"])
    assert result == {"orderId": "201"}


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_market_order_retry_uses_same_client_order_id(
    mock_client_cls: MagicMock,
) -> None:
    """Il retry del market order deve riusare lo stesso newClientOrderId."""
    mock_instance = mock_client_cls.return_value
    _setup_symbol_info(mock_instance)
    mock_instance.get_symbol_ticker.return_value = {"price": "50000.0"}
    mock_instance.order_market_buy.side_effect = [
        BinanceRequestException("Connection error"),
        {"orderId": "102"},
    ]

    client = BinanceClient(_make_settings())
    result = client.place_market_order("BTCUSDC", "BUY", 0.001)

    assert result == {"orderId": "102"}
    assert mock_instance.order_market_buy.call_count == 2
    first_kwargs = mock_instance.order_market_buy.call_args_list[0].kwargs
    second_kwargs = mock_instance.order_market_buy.call_args_list[1].kwargs
    assert first_kwargs["newClientOrderId"] == second_kwargs["newClientOrderId"]
    _assert_valid_uuid4(first_kwargs["newClientOrderId"])


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_limit_order_retry_uses_same_client_order_id(
    mock_client_cls: MagicMock,
) -> None:
    """Il retry del limit order deve riusare lo stesso newClientOrderId."""
    mock_instance = mock_client_cls.return_value
    _setup_symbol_info(mock_instance)
    mock_instance.order_limit_sell.side_effect = [
        BinanceRequestException("Connection error"),
        {"orderId": "202"},
    ]

    client = BinanceClient(_make_settings())
    result = client.place_limit_order("BTCUSDC", "SELL", 0.001, 99000.0)

    assert result == {"orderId": "202"}
    assert mock_instance.order_limit_sell.call_count == 2
    first_kwargs = mock_instance.order_limit_sell.call_args_list[0].kwargs
    second_kwargs = mock_instance.order_limit_sell.call_args_list[1].kwargs
    assert first_kwargs["newClientOrderId"] == second_kwargs["newClientOrderId"]
    _assert_valid_uuid4(first_kwargs["newClientOrderId"])


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_market_order_invalid_side_raises(mock_client_cls: MagicMock) -> None:
    """place_market_order con side non valido deve lanciare ValueError."""
    client = BinanceClient(_make_settings())

    with pytest.raises(ValueError, match="Invalid order side"):
        client.place_market_order("BTCUSDC", "HOLD", 0.001)


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_limit_order_invalid_side_raises(mock_client_cls: MagicMock) -> None:
    """place_limit_order con side non valido deve lanciare ValueError."""
    client = BinanceClient(_make_settings())

    with pytest.raises(ValueError, match="Invalid order side"):
        client.place_limit_order("BTCUSDC", "HOLD", 0.001, 97000.0)


# ---------- Verifica quantize filtri LOT_SIZE / PRICE_FILTER / NOTIONAL ----------


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_limit_order_quantizes_quantity_to_step_size(
    mock_client_cls: MagicMock,
) -> None:
    """Quantity con troppe cifre decimali viene troncata al multiplo inferiore di stepSize."""
    mock_instance = mock_client_cls.return_value
    _setup_symbol_info(mock_instance, step_size="0.00001", min_qty="0.00001")
    mock_instance.order_limit_sell.return_value = {"orderId": "500"}

    client = BinanceClient(_make_settings())
    client.place_limit_order("BTCUSDC", "SELL", 0.0099905, 99000.0)

    _, kwargs = mock_instance.order_limit_sell.call_args
    assert kwargs["quantity"] == Decimal("0.00999")


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_limit_order_quantizes_price_to_tick_size(
    mock_client_cls: MagicMock,
) -> None:
    """Price con troppi decimali viene troncato al multiplo inferiore di tickSize."""
    mock_instance = mock_client_cls.return_value
    _setup_symbol_info(mock_instance, tick_size="0.01")
    mock_instance.order_limit_buy.return_value = {"orderId": "501"}

    client = BinanceClient(_make_settings())
    client.place_limit_order("BTCUSDC", "BUY", 0.01, 97000.12345)

    _, kwargs = mock_instance.order_limit_buy.call_args
    assert kwargs["price"] == "97000.12"


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_limit_order_rejects_below_min_qty(
    mock_client_cls: MagicMock,
) -> None:
    """Quantity sotto minQty (anche dopo rounding) deve sollevare ValueError."""
    mock_instance = mock_client_cls.return_value
    _setup_symbol_info(mock_instance, step_size="0.00001", min_qty="0.001")

    client = BinanceClient(_make_settings())
    with pytest.raises(ValueError, match="minQty"):
        client.place_limit_order("BTCUSDC", "SELL", 0.0005, 50000.0)

    mock_instance.order_limit_sell.assert_not_called()


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_limit_order_rejects_below_min_notional(
    mock_client_cls: MagicMock,
) -> None:
    """Ordine sotto minNotional (quantity * price) deve sollevare ValueError."""
    mock_instance = mock_client_cls.return_value
    _setup_symbol_info(
        mock_instance, step_size="0.00001", min_qty="0.00001", min_notional="10.0",
    )

    client = BinanceClient(_make_settings())
    with pytest.raises(ValueError, match="minNotional"):
        client.place_limit_order("BTCUSDC", "BUY", 0.0001, 50.0)

    mock_instance.order_limit_buy.assert_not_called()


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_symbol_filters_are_cached(mock_client_cls: MagicMock) -> None:
    """get_symbol_info deve essere chiamato una sola volta per simbolo."""
    mock_instance = mock_client_cls.return_value
    _setup_symbol_info(mock_instance)
    mock_instance.get_symbol_ticker.return_value = {"price": "50000.0"}
    mock_instance.order_market_buy.return_value = {"orderId": "600"}
    mock_instance.order_market_sell.return_value = {"orderId": "601"}
    mock_instance.order_limit_buy.return_value = {"orderId": "602"}

    client = BinanceClient(_make_settings())
    client.place_market_order("BTCUSDC", "BUY", 0.001)
    client.place_market_order("BTCUSDC", "SELL", 0.001)
    client.place_limit_order("BTCUSDC", "BUY", 0.001, 50000.0)

    assert mock_instance.get_symbol_info.call_count == 1


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


# ---------- Verifica place_oco_sell ----------


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_oco_sell_calls_create_oco_order_with_correct_params(
    mock_client_cls: MagicMock,
) -> None:
    """place_oco_sell deve chiamare create_oco_order con i parametri quantizzati corretti."""
    mock_instance = mock_client_cls.return_value
    _setup_symbol_info(
        mock_instance,
        step_size="0.00001",
        min_qty="0.00001",
        tick_size="0.01",
        min_notional="10.0",
    )
    mock_instance.create_oco_order.return_value = {
        "orderListId": 42,
        "orders": [{"orderId": "200"}, {"orderId": "201"}],
    }

    client = BinanceClient(_make_settings())
    result = client.place_oco_sell(
        symbol="BTCUSDC",
        quantity=0.003,
        tp_price=115_000.0,
        sl_stop_price=92_000.0,
    )

    assert result["orderListId"] == 42

    call_kwargs = mock_instance.create_oco_order.call_args.kwargs
    assert call_kwargs["symbol"] == "BTCUSDC"
    assert call_kwargs["side"] == "SELL"
    assert call_kwargs["quantity"] == Decimal("0.00300")
    assert call_kwargs["aboveType"] == "LIMIT_MAKER"
    assert call_kwargs["abovePrice"] == "115000.00"
    assert call_kwargs["belowType"] == "STOP_LOSS_LIMIT"
    assert call_kwargs["belowStopPrice"] == "92000.00"
    # sl_limit_price = 92000 * 0.995 = 91540 → troncato a tickSize 0.01
    assert call_kwargs["belowPrice"] == "91540.00"
    assert call_kwargs["belowTimeInForce"] == "GTC"
    _assert_valid_uuid4(call_kwargs["listClientOrderId"])


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_oco_sell_quantizes_prices(mock_client_cls: MagicMock) -> None:
    """place_oco_sell quantizza tp_price e sl_stop_price al tickSize."""
    mock_instance = mock_client_cls.return_value
    _setup_symbol_info(mock_instance, tick_size="1.0", min_notional="10.0")
    mock_instance.create_oco_order.return_value = {"orderListId": 1, "orders": []}

    client = BinanceClient(_make_settings())
    client.place_oco_sell(
        symbol="BTCUSDC",
        quantity=0.001,
        tp_price=115_000.99,   # deve essere troncato a 115000
        sl_stop_price=92_000.75,  # deve essere troncato a 92000
    )

    call_kwargs = mock_instance.create_oco_order.call_args.kwargs
    assert call_kwargs["abovePrice"] == "115000.0"
    assert call_kwargs["belowStopPrice"] == "92000.0"


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_oco_sell_passes_list_client_order_id(
    mock_client_cls: MagicMock,
) -> None:
    """place_oco_sell deve passare listClientOrderId a create_oco_order."""
    mock_instance = mock_client_cls.return_value
    _setup_symbol_info(mock_instance)
    mock_instance.create_oco_order.return_value = {"orderListId": 99, "orders": []}

    client = BinanceClient(_make_settings())
    client.place_oco_sell(
        symbol="BTCUSDC",
        quantity=0.001,
        tp_price=115_000.0,
        sl_stop_price=92_000.0,
    )

    call_kwargs = mock_instance.create_oco_order.call_args.kwargs
    _assert_valid_uuid4(call_kwargs["listClientOrderId"])


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_place_oco_sell_retry_uses_same_list_client_order_id(
    mock_client_cls: MagicMock,
) -> None:
    """Il retry dell'OCO sell deve riusare lo stesso listClientOrderId."""
    mock_instance = mock_client_cls.return_value
    _setup_symbol_info(mock_instance)
    mock_instance.create_oco_order.side_effect = [
        BinanceRequestException("Connection error"),
        {"orderListId": 43, "orders": []},
    ]

    client = BinanceClient(_make_settings())
    result = client.place_oco_sell(
        symbol="BTCUSDC",
        quantity=0.001,
        tp_price=115_000.0,
        sl_stop_price=92_000.0,
    )

    assert result["orderListId"] == 43
    assert mock_instance.create_oco_order.call_count == 2
    first_kwargs = mock_instance.create_oco_order.call_args_list[0].kwargs
    second_kwargs = mock_instance.create_oco_order.call_args_list[1].kwargs
    assert first_kwargs["listClientOrderId"] == second_kwargs["listClientOrderId"]
    _assert_valid_uuid4(first_kwargs["listClientOrderId"])


# ---------- Verifica cancel_oco ----------


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_cancel_oco_calls_cancel_order_list_with_correct_params(
    mock_client_cls: MagicMock,
) -> None:
    """cancel_oco deve chiamare cancel_order_list con symbol e orderListId corretti."""
    mock_instance = mock_client_cls.return_value
    mock_instance.cancel_order_list.return_value = {
        "orderListId": 99,
        "contingencyType": "OCO",
        "listStatusType": "ALL_DONE",
    }

    client = BinanceClient(_make_settings())
    result = client.cancel_oco("BTCUSDC", 99)

    mock_instance.cancel_order_list.assert_called_once_with(
        symbol="BTCUSDC", orderListId=99,
    )
    assert result["orderListId"] == 99


@patch("src.integrations.exchange.binance_client.BinanceApiClient")
def test_cancel_oco_retries_on_transient_error(mock_client_cls: MagicMock) -> None:
    """cancel_oco deve riprovare su BinanceRequestException (errore transitorio)."""
    mock_instance = mock_client_cls.return_value
    mock_instance.cancel_order_list.side_effect = [
        BinanceRequestException("connection error"),
        {"orderListId": 99, "listStatusType": "ALL_DONE"},
    ]

    client = BinanceClient(_make_settings())
    result = client.cancel_oco("BTCUSDC", 99)

    assert result["orderListId"] == 99
    assert mock_instance.cancel_order_list.call_count == 2
