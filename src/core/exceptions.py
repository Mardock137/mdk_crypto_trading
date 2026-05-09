from __future__ import annotations


class MdkTradingError(Exception):
    """Base per tutti gli errori operativi attesi."""


class ExchangeError(MdkTradingError):
    """Errore proveniente dall'exchange (Binance API error, rete, ecc.)."""


class LlmError(MdkTradingError, RuntimeError):
    """Errore proveniente da un provider LLM.

    Eredita da entrambi ``MdkTradingError`` e ``RuntimeError`` per garantire
    la compatibilità con il codice che cattura ``RuntimeError`` direttamente.
    """
