from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.contracts import NewsArticle


class BaseNewsClient(ABC):
    """Interfaccia astratta per i client di notizie crypto.

    Ogni implementazione concreta rappresenta una fonte sostituibile:
    lo stesso contratto vale per Alpha Vantage, CryptoPanic, ecc.
    """

    @abstractmethod
    def get_recent_news(self) -> list[NewsArticle]:
        """Scarica le notizie recenti e le restituisce come lista di NewsArticle."""
