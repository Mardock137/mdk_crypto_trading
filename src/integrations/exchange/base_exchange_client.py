from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseExchangeClient(ABC):
    """Interfaccia astratta per i client degli exchange di criptovalute."""

    @abstractmethod
    def ping(self) -> bool:
        """Verifica che l'exchange sia raggiungibile."""

    @abstractmethod
    def get_account_info(self) -> dict[str, Any]:
        """Recupera le informazioni dell'account (verifica autenticazione)."""
