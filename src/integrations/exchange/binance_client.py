from __future__ import annotations

from typing import Any

from binance.client import Client as BinanceApiClient

from src.integrations.exchange.base_exchange_client import BaseExchangeClient
from src.utils.config import AppSettings, TradingMode


class BinanceClient(BaseExchangeClient):
    """Client Binance con supporto per modalità DEMO e REAL."""

    def __init__(self, settings: AppSettings) -> None:
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

    def ping(self) -> bool:
        self._client.ping()
        return True

    def get_account_info(self) -> dict[str, Any]:
        result: dict[str, Any] = self._client.get_account()
        return result
