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
