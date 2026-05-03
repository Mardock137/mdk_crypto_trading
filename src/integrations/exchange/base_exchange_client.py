from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.core.contracts import MarketDataSnapshot, PortfolioState


class BaseExchangeClient(ABC):
    """Interfaccia astratta per i client degli exchange di criptovalute."""

    @abstractmethod
    def ping(self) -> bool:
        """Verifica che l'exchange sia raggiungibile."""

    @abstractmethod
    def get_account_info(self) -> dict[str, Any]:
        """Recupera le informazioni dell'account (verifica autenticazione)."""

    @abstractmethod
    def get_market_snapshot(self, symbol: str) -> MarketDataSnapshot:
        """Raccoglie uno snapshot completo dei dati di mercato per il simbolo."""

    @abstractmethod
    def get_portfolio_state(self, symbol: str) -> PortfolioState:
        """Raccoglie lo stato del portafoglio per il simbolo."""

    @abstractmethod
    def place_market_order(
        self, symbol: str, side: str, quantity: float,
    ) -> dict[str, Any]:
        """Piazza un ordine a mercato (BUY o SELL)."""

    @abstractmethod
    def place_limit_order(
        self, symbol: str, side: str, quantity: float, price: float,
    ) -> dict[str, Any]:
        """Piazza un ordine limit (BUY o SELL)."""

    @abstractmethod
    def cancel_order(self, symbol: str, order_id: str) -> dict[str, Any]:
        """Cancella un ordine aperto tramite il suo ID."""

    @abstractmethod
    def place_oco_sell(
        self,
        symbol: str,
        quantity: float,
        tp_price: float,
        sl_stop_price: float,
    ) -> dict[str, Any]:
        """Piazza OCO SELL: take profit LIMIT + stop loss STOP_LOSS_LIMIT."""
