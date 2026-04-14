from __future__ import annotations

from typing import Any

from binance.client import Client as BinanceApiClient
from binance.exceptions import BinanceAPIException, BinanceRequestException
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.core.contracts import MarketDataSnapshot, PortfolioState
from src.integrations.exchange.base_exchange_client import BaseExchangeClient
from src.utils.config import AppSettings, TradingMode
from src.utils import indicators


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, BinanceRequestException):
        return True
    if isinstance(exc, BinanceAPIException):
        return exc.status_code in (429, 418) or exc.status_code >= 500
    return False


_binance_retry = retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    reraise=True,
)


class BinanceClient(BaseExchangeClient):
    """Client Binance con supporto per modalità DEMO e REAL."""

    def __init__(self, settings: AppSettings, *, quote_currency: str = "USDC") -> None:
        self._quote_currency = quote_currency
        if settings.trading_mode == TradingMode.DEMO:
            if not settings.binance_demo_api_key or not settings.binance_demo_secret_key:
                raise ValueError(
                    "Modalità DEMO: binance_demo_api_key e "
                    "binance_demo_secret_key sono obbligatorie."
                )
            if not settings.binance_demo_base_url:
                raise ValueError(
                    "Modalità DEMO: binance_demo_base_url è obbligatoria."
                )
            self._client = BinanceApiClient(
                api_key=settings.binance_demo_api_key,
                api_secret=settings.binance_demo_secret_key,
            )
            self._client.API_URL = settings.binance_demo_base_url
        else:
            if not settings.binance_api_key or not settings.binance_secret_key:
                raise ValueError(
                    "Modalità REAL: binance_api_key e "
                    "binance_secret_key sono obbligatorie."
                )
            self._client = BinanceApiClient(
                api_key=settings.binance_api_key,
                api_secret=settings.binance_secret_key,
            )

    # ---- Metodi base ----

    @_binance_retry
    def ping(self) -> bool:
        try:
            self._client.ping()
            return True
        except Exception:
            return False

    @_binance_retry
    def get_account_info(self) -> dict[str, Any]:
        result: dict[str, Any] = self._client.get_account()
        return result

    # ---- Dati di mercato ----

    @_binance_retry
    def get_market_snapshot(self, symbol: str) -> MarketDataSnapshot:
        price = float(self._client.get_symbol_ticker(symbol=symbol)["price"])
        avg_price = float(self._client.get_avg_price(symbol=symbol)["price"])
        ticker_24h = self._client.get_ticker(symbol=symbol)
        volume_24h = float(ticker_24h["volume"])

        order_book = self._client.get_order_book(symbol=symbol, limit=10)

        candles = self._fetch_candles(symbol)

        # Indicatori calcolati sulle kline 1h (almeno 60 candele)
        closes_1h = self._get_hourly_closes(symbol)
        indicator_values = self._compute_indicators(closes_1h)

        return MarketDataSnapshot(
            symbol=symbol,
            price=price,
            avg_price=avg_price,
            volume_24h=volume_24h,
            order_book_top_10_bids=order_book.get("bids", []),
            order_book_top_10_asks=order_book.get("asks", []),
            indicators=indicator_values,
            candles=candles,
        )

    @_binance_retry
    def get_portfolio_state(self, symbol: str) -> PortfolioState:
        account = self._client.get_account()
        balances = {b["asset"]: b for b in account.get("balances", [])}

        coin = symbol.removesuffix(self._quote_currency)

        usdc = balances.get(self._quote_currency, {})
        usdc_free = float(usdc.get("free", 0))
        usdc_locked = float(usdc.get("locked", 0))

        coin_balance = balances.get(coin, {})
        coin_free = float(coin_balance.get("free", 0))
        coin_locked = float(coin_balance.get("locked", 0))

        # Stima del controvalore in USDC della coin posseduta
        try:
            coin_price = float(
                self._client.get_symbol_ticker(symbol=symbol)["price"]
            )
        except Exception:
            coin_price = 0.0
        usdc_value = (coin_free + coin_locked) * coin_price

        open_orders = self._client.get_open_orders(symbol=symbol)
        last_trades = self._client.get_my_trades(symbol=symbol, limit=10)

        snapshot = (
            f"{self._quote_currency}: {usdc_free:.2f} free / {usdc_free + usdc_locked:.2f} total | "
            f"{coin}: {coin_free} free / {coin_free + coin_locked} total"
        )

        return PortfolioState(
            usdc_balance=usdc_free,
            usdc_balance_total=usdc_free + usdc_locked,
            usdc_value=usdc_value,
            portfolio_qty_free=coin_free,
            portfolio_qty_total=coin_free + coin_locked,
            portfolio_snapshot=snapshot,
            open_orders=open_orders,
            last_trades=last_trades,
        )

    # ---- Esecuzione ordini ----

    def place_market_order(
        self, symbol: str, side: str, quantity: float,
    ) -> dict[str, Any]:
        normalized = side.upper()
        if normalized == "BUY":
            result: dict[str, Any] = self._client.order_market_buy(
                symbol=symbol, quantity=quantity,
            )
        elif normalized == "SELL":
            result = self._client.order_market_sell(
                symbol=symbol, quantity=quantity,
            )
        else:
            raise ValueError(f"Invalid order side: {side!r}. Expected 'BUY' or 'SELL'.")
        return result

    def place_limit_order(
        self, symbol: str, side: str, quantity: float, price: float,
    ) -> dict[str, Any]:
        normalized = side.upper()
        if normalized == "BUY":
            result: dict[str, Any] = self._client.order_limit_buy(
                symbol=symbol, quantity=quantity, price=str(price),
                timeInForce="GTC",
            )
        elif normalized == "SELL":
            result = self._client.order_limit_sell(
                symbol=symbol, quantity=quantity, price=str(price),
                timeInForce="GTC",
            )
        else:
            raise ValueError(f"Invalid order side: {side!r}. Expected 'BUY' or 'SELL'.")
        return result

    def cancel_order(self, symbol: str, order_id: str) -> dict[str, Any]:
        result: dict[str, Any] = self._client.cancel_order(
            symbol=symbol, orderId=order_id,
        )
        return result

    # ---- Helper privati ----

    def _fetch_candles(self, symbol: str) -> dict[str, Any]:
        """Recupera le candele per i timeframe richiesti dal Market Analyst."""
        intervals: dict[str, tuple[str, int]] = {
            "candles_2h": ("2h", 12),
            "candles_4h": ("4h", 14),
            "candles_1d": ("1d", 14),
            "candles_1w": ("1w", 8),
            "candles_1M": ("1M", 6),
        }
        candles: dict[str, Any] = {}
        for key, (interval, limit) in intervals.items():
            raw = self._client.get_klines(
                symbol=symbol, interval=interval, limit=limit,
            )
            candles[key] = [
                {
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                }
                for k in raw
            ]
        return candles

    def _get_hourly_closes(self, symbol: str) -> list[float]:
        """Recupera i prezzi di chiusura delle ultime 60 candele 1h."""
        raw = self._client.get_klines(
            symbol=symbol, interval="1h", limit=60,
        )
        return [float(k[4]) for k in raw]

    def _compute_indicators(
        self, closes: list[float],
    ) -> dict[str, float | None]:
        """Calcola tutti gli indicatori tecnici e i valori precedenti."""
        # Valori attuali (su tutta la serie) e precedenti (serie senza l'ultimo valore)
        closes_prev = closes[:-1] if len(closes) > 1 else closes

        rsi_val = indicators.rsi(closes, period=14)
        rsi_prev = indicators.rsi(closes_prev, period=14)

        ema_val = indicators.ema(closes, period=21)
        ema_prev = indicators.ema(closes_prev, period=21)

        sma_val = indicators.sma(closes, period=50)
        sma_prev = indicators.sma(closes_prev, period=50)

        macd_val = indicators.macd(closes)
        macd_prev = indicators.macd(closes_prev)

        return {
            "rsi_14": rsi_val,
            "rsi_14_prev": rsi_prev,
            "ema_21": ema_val,
            "ema_21_prev": ema_prev,
            "sma_50": sma_val,
            "sma_50_prev": sma_prev,
            "macd": macd_val[0] if macd_val else None,
            "macd_prev": macd_prev[0] if macd_prev else None,
            "macd_signal": macd_val[1] if macd_val else None,
            "macd_signal_prev": macd_prev[1] if macd_prev else None,
            "macd_hist": macd_val[2] if macd_val else None,
            "macd_hist_prev": macd_prev[2] if macd_prev else None,
        }
