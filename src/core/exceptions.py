from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.contracts import MarketAnalysis, RiskAssessment, TradeProposal


class MdkTradingError(Exception):
    """Base per tutti gli errori operativi attesi."""


class ExchangeError(MdkTradingError):
    """Errore proveniente dall'exchange (Binance API error, rete, ecc.)."""


class LlmError(MdkTradingError, RuntimeError):
    """Errore proveniente da un provider LLM.

    Eredita da entrambi ``MdkTradingError`` e ``RuntimeError`` per garantire
    la compatibilità con il codice che cattura ``RuntimeError`` direttamente.
    """


class CycleExecutionError(MdkTradingError):
    """Errore durante un ciclo di trading: porta con sé i risultati parziali.

    Sollevata da ``TradingWorkflow.run_cycle`` quando uno degli step (Market
    Analyst, Decision Maker, Risk Manager, Execution Trader) fallisce. Trasporta
    gli output già prodotti dagli step precedenti in modo che il runner possa
    salvarli nel log eventi per debug post-mortem.
    """

    def __init__(
        self,
        message: str,
        *,
        original: BaseException,
        market_analysis: MarketAnalysis | None = None,
        trade_proposal: TradeProposal | None = None,
        risk_assessment: RiskAssessment | None = None,
    ) -> None:
        super().__init__(message)
        self.original = original
        self.market_analysis = market_analysis
        self.trade_proposal = trade_proposal
        self.risk_assessment = risk_assessment
