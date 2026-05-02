from __future__ import annotations

import logging
from decimal import ROUND_DOWN, Decimal
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

logger = logging.getLogger(__name__)


class BinanceClient(BaseExchangeClient):
    """Client Binance con supporto per modalità DEMO e REAL."""

    def __init__(self, settings: AppSettings, *, quote_currency: str = "USDC") -> None:
        self._quote_currency = quote_currency
        self._symbol_filters_cache: dict[str, dict[str, Decimal]] = {}
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

        # Indicatori calcolati sulle kline 1h (almeno 60 candele).
        # Il calcolo vero e proprio vive in src/utils/indicators.py: l'exchange si
        # limita a fetchare i closes e a delegare il bundle.
        closes_1h = self._get_hourly_closes(symbol)
        indicator_values = indicators.compute_indicators_bundle(closes_1h)
        if (
            indicator_values.get("rsi") is None
            and indicator_values.get("macd") is not None
        ):
            logger.warning(
                "RSI unavailable while MACD is available for %s; closes_1h=%d",
                symbol,
                len(closes_1h),
            )

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

    # NOTE: nessun @_binance_retry su place_market_order/place_limit_order.
    # Senza idempotency key (newClientOrderId) un retry su risposta persa per timeout
    # potrebbe creare un secondo ordine duplicato. La gestione di un'eventuale failure
    # transiente sugli ordini è demandata al chiamante (ExecutionTraderAgent).
    def place_market_order(
        self, symbol: str, side: str, quantity: float,
    ) -> dict[str, Any]:
        normalized = side.upper()
        if normalized not in ("BUY", "SELL"):
            raise ValueError(f"Invalid order side: {side!r}. Expected 'BUY' or 'SELL'.")

        # Per i MARKET order usiamo il prezzo corrente per validare minNotional.
        reference_price = Decimal(
            str(self._client.get_symbol_ticker(symbol=symbol)["price"])
        )
        adjusted_qty = self._quantize_quantity(
            symbol, Decimal(str(quantity)), reference_price,
        )

        if normalized == "BUY":
            result: dict[str, Any] = self._client.order_market_buy(
                symbol=symbol, quantity=adjusted_qty,
            )
        else:
            result = self._client.order_market_sell(
                symbol=symbol, quantity=adjusted_qty,
            )
        return result

    # Stessa motivazione di place_market_order: nessun retry per evitare ordini
    # duplicati in caso di risposta persa per timeout.
    def place_limit_order(
        self, symbol: str, side: str, quantity: float, price: float,
    ) -> dict[str, Any]:
        normalized = side.upper()
        if normalized not in ("BUY", "SELL"):
            raise ValueError(f"Invalid order side: {side!r}. Expected 'BUY' or 'SELL'.")

        adjusted_price = self._quantize_price(symbol, Decimal(str(price)))
        adjusted_qty = self._quantize_quantity(
            symbol, Decimal(str(quantity)), adjusted_price,
        )

        if normalized == "BUY":
            result: dict[str, Any] = self._client.order_limit_buy(
                symbol=symbol, quantity=adjusted_qty, price=str(adjusted_price),
                timeInForce="GTC",
            )
        else:
            result = self._client.order_limit_sell(
                symbol=symbol, quantity=adjusted_qty, price=str(adjusted_price),
                timeInForce="GTC",
            )
        return result

    @_binance_retry
    def cancel_order(self, symbol: str, order_id: str) -> dict[str, Any]:
        # Cancel è idempotente lato Binance: cancellare due volte un ordine
        # già cancellato/inesistente è innocuo, quindi il retry è sicuro.
        result: dict[str, Any] = self._client.cancel_order(
            symbol=symbol, orderId=order_id,
        )
        return result

    # ---- Helper privati ----

    def _get_symbol_filters(self, symbol: str) -> dict[str, Decimal]:
        """Recupera e mette in cache i filtri Binance per il simbolo.

        Filtri estratti: stepSize e minQty (LOT_SIZE), tickSize (PRICE_FILTER),
        minNotional (NOTIONAL o MIN_NOTIONAL). I valori sono Decimal per
        evitare errori floating-point nel rounding.
        """
        cached = self._symbol_filters_cache.get(symbol)
        if cached is not None:
            return cached

        info = self._client.get_symbol_info(symbol)
        if not info:
            raise ValueError(f"Symbol info not found for {symbol!r}")

        filters = {f["filterType"]: f for f in info.get("filters", [])}

        lot_size = filters.get("LOT_SIZE", {})
        price_filter = filters.get("PRICE_FILTER", {})
        notional = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL") or {}

        step_size = Decimal(str(lot_size.get("stepSize", "0")))
        min_qty = Decimal(str(lot_size.get("minQty", "0")))
        tick_size = Decimal(str(price_filter.get("tickSize", "0")))
        min_notional = Decimal(
            str(notional.get("minNotional") or notional.get("notional") or "0")
        )

        parsed: dict[str, Decimal] = {
            "stepSize": step_size,
            "minQty": min_qty,
            "tickSize": tick_size,
            "minNotional": min_notional,
        }
        self._symbol_filters_cache[symbol] = parsed
        return parsed

    @staticmethod
    def _quantize_down(value: Decimal, step: Decimal) -> Decimal:
        """Tronca `value` al multiplo inferiore piu vicino di `step`."""
        if step <= 0:
            return value
        quantized = (value / step).to_integral_value(rounding=ROUND_DOWN) * step
        # Normalizza il numero di decimali a quello di `step` per evitare
        # stringhe come "0.00100000000" quando poi viene passato a Binance.
        return quantized.quantize(step)

    def _quantize_quantity(
        self, symbol: str, quantity: Decimal, reference_price: Decimal,
    ) -> Decimal:
        """Tronca la quantity a `stepSize` e valida `minQty` / `minNotional`."""
        filters = self._get_symbol_filters(symbol)
        step = filters["stepSize"]
        min_qty = filters["minQty"]
        min_notional = filters["minNotional"]

        adjusted = self._quantize_down(quantity, step) if step > 0 else quantity

        if adjusted <= 0:
            raise ValueError(
                f"Quantity {quantity} per {symbol} troppo piccola: "
                f"dopo il rounding a stepSize={step} risulta {adjusted}."
            )
        if min_qty > 0 and adjusted < min_qty:
            raise ValueError(
                f"Quantity {adjusted} per {symbol} sotto il minQty {min_qty} "
                f"imposto da Binance."
            )
        if (
            min_notional > 0
            and reference_price > 0
            and adjusted * reference_price < min_notional
        ):
            raise ValueError(
                f"Valore ordine {adjusted * reference_price} USDC per {symbol} "
                f"sotto il minNotional {min_notional} imposto da Binance."
            )
        return adjusted

    def _quantize_price(self, symbol: str, price: Decimal) -> Decimal:
        """Tronca il price a `tickSize`."""
        filters = self._get_symbol_filters(symbol)
        tick = filters["tickSize"]
        if tick <= 0:
            return price
        adjusted = self._quantize_down(price, tick)
        if adjusted <= 0:
            raise ValueError(
                f"Price {price} per {symbol} troppo piccolo: "
                f"dopo il rounding a tickSize={tick} risulta {adjusted}."
            )
        return adjusted

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
