from __future__ import annotations

import logging

from src.core.contracts import (
    CycleContextSnapshot,
    CycleSkipConfig,
    MarketDataSnapshot,
    PortfolioState,
    TradeAction,
)
from src.utils.cycle_skip import extract_open_order_ids, should_skip_cycle
from src.utils.event_logger import EventLogger


class CycleSkipHandler:
    """Gestisce la decisione di saltare un ciclo e lo stato cross-cycle.

    Possiede lo snapshot del ciclo precedente e il counter dei salti
    consecutivi: stato che prima viveva sparso nel ``TradingRunner``.
    """

    def __init__(
        self,
        symbol: str,
        trading_mode: str,
        config: CycleSkipConfig,
        event_logger: EventLogger,
        logger: logging.Logger,
    ) -> None:
        self._symbol = symbol
        self._trading_mode = trading_mode
        self._config = config
        self._event_logger = event_logger
        self._logger = logger
        self._previous_snapshot: CycleContextSnapshot | None = None
        self._consecutive_skips: int = 0

    def try_skip(
        self,
        market_data: MarketDataSnapshot,
        portfolio: PortfolioState,
    ) -> bool:
        """Decide se saltare il ciclo corrente. Se sì, logga e aggiorna il counter."""
        if not self._config.enabled:
            return False

        skip, reason = should_skip_cycle(
            previous=self._previous_snapshot,
            current_market=market_data,
            current_portfolio=portfolio,
            config=self._config,
            consecutive_skips=self._consecutive_skips,
        )
        if not skip:
            self._logger.debug("Cycle skip non applicabile: %s", reason)
            return False

        assert self._previous_snapshot is not None
        self._logger.info("Ciclo saltato dal pre-check deterministico: %s", reason)
        self._event_logger.log_skipped_cycle(
            symbol=self._symbol,
            trading_mode=self._trading_mode,
            reason=reason,
            snapshot=self._previous_snapshot,
        )
        self._consecutive_skips += 1
        return True

    def record_completed_cycle(
        self,
        market_data: MarketDataSnapshot,
        portfolio: PortfolioState,
        proposed_action: TradeAction,
    ) -> None:
        """Aggiorna lo snapshot e azzera il counter dopo un ciclo eseguito."""
        self._previous_snapshot = _build_snapshot(
            market_data=market_data,
            portfolio=portfolio,
            proposed_action=proposed_action,
        )
        self._consecutive_skips = 0


def _build_snapshot(
    market_data: MarketDataSnapshot,
    portfolio: PortfolioState,
    proposed_action: TradeAction,
) -> CycleContextSnapshot:
    """Costruisce uno snapshot del contesto del ciclo appena concluso.

    ``proposed_action`` è l'azione proposta dal Decision Maker (non quella
    effettivamente eseguita). Scelta voluta: se il DM propone BUY/SELL ma
    il Risk Manager blocca, il ciclo successivo deve comunque girare per
    dare al DM l'opportunità di rivalutare, quindi il pre-check non deve
    saltarlo.
    """
    indicators = market_data.indicators
    return CycleContextSnapshot(
        price=market_data.price,
        rsi=_coerce_float(indicators.get("rsi")),
        macd=_coerce_float(indicators.get("macd")),
        macd_signal=_coerce_float(indicators.get("macd_signal")),
        previous_action=proposed_action,
        open_order_ids=extract_open_order_ids(portfolio),
    )


def _coerce_float(value: object) -> float | None:
    """Converte un valore in ``float``, ritornando ``None`` se non possibile."""
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
