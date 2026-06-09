from __future__ import annotations

import logging

from src.core.contracts import MarketDataSnapshot, PortfolioState
from src.integrations.exchange.base_exchange_client import BaseExchangeClient
from src.utils.memory_manager import MemoryManager

# Tolleranza relativa oltre la quale open_qty (FIFO) e qty_total (exchange) vengono
# considerati divergenti e viene emesso un WARNING diagnostico.
_POSITION_QTY_TOLERANCE = 0.01

# Chiavi dei dizionari ordine Binance
_ORDER_TYPE = "type"
_TYPE_LIMIT_MAKER = "LIMIT_MAKER"
_TYPE_STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"
_ORDER_LIST_ID = "orderListId"
_STOP_PRICE = "stopPrice"
_ORIG_QTY = "origQty"
_ORDER_PRICE = "price"
_AGE_HOURS = "age_hours"


class PositionManager:
    """Gestisce la posizione aperta: calcolo P&L FIFO, breakeven automatico OCO e flag oco_review_required."""

    def __init__(
        self,
        symbol: str,
        exchange_client: BaseExchangeClient,
        memory_manager: MemoryManager,
        kill_switch: bool,
        breakeven_trigger_pct: float,
        oco_review_interval_hours: float,
        logger: logging.Logger,
    ) -> None:
        self._symbol = symbol
        self._exchange_client = exchange_client
        self._memory_manager = memory_manager
        self._kill_switch = kill_switch
        self._breakeven_trigger_pct = breakeven_trigger_pct
        self._oco_review_interval_hours = oco_review_interval_hours
        self._logger = logger

    def augment_portfolio_with_open_position(
        self,
        market_data: MarketDataSnapshot,
        portfolio: PortfolioState,
    ) -> None:
        """Calcola e popola avg_entry_price, unrealized_pnl_pct e unrealized_pnl_usdc sul portafoglio.

        Usa la coda FIFO dei lotti BUY non ancora consumati gestita da MemoryManager.
        Se non c'e posizione aperta, mancano dati validi o un calcolo fallisce,
        lascia i campi a None senza interrompere il ciclo: si tratta di metadati
        opzionali che arricchiscono il prompt del Decision Maker.
        """
        try:
            qty_total = float(portfolio.portfolio_qty_total)
            price = float(market_data.price) if market_data.price is not None else None
        except (TypeError, ValueError):
            return
        if qty_total <= 0 or price is None or price <= 0:
            return
        try:
            open_pos = self._memory_manager.compute_open_position(self._symbol)
        except Exception:  # pragma: no cover — fallback difensivo
            return
        if not open_pos:
            return
        try:
            avg_entry = float(open_pos["avg_entry_price"])
            open_qty = float(open_pos["open_qty"])
        except (TypeError, ValueError, KeyError):
            return
        if avg_entry <= 0 or open_qty <= 0:
            return
        portfolio.avg_entry_price = avg_entry
        portfolio.unrealized_pnl_pct = round(
            (price - avg_entry) / avg_entry * 100, 4
        )
        portfolio.unrealized_pnl_usdc = round((price - avg_entry) * open_qty, 4)
        if qty_total > 0 and abs(open_qty - qty_total) / qty_total > _POSITION_QTY_TOLERANCE:
            self._logger.warning(
                "Divergenza posizione: FIFO open_qty=%s vs saldo exchange qty_total=%s "
                "(memoria possibilmente disallineata)",
                open_qty,
                qty_total,
            )

    def maybe_apply_breakeven(self, portfolio: PortfolioState) -> None:
        """Sposta lo SL dell'OCO attivo al breakeven se il profitto supera la soglia.

        Condizioni necessarie (tutte e quattro):
        1. unrealized_pnl_pct valorizzato e >= breakeven_trigger_pct
        2. avg_entry_price valorizzato
        3. open_orders contiene un LIMIT_MAKER (TP) e un STOP_LOSS_LIMIT (SL)
           con lo stesso orderListId (OCO attivo)
        4. Il stopPrice dell'SL è sotto avg_entry_price (breakeven non ancora attivo)

        Se le condizioni sono soddisfatte: cancella l'OCO e piazza un nuovo OCO
        con lo stesso TP e lo SL trigger = avg_entry_price.
        Gli errori vengono loggati come WARNING senza interrompere il ciclo.
        """
        if self._kill_switch:
            self._logger.debug("Kill switch attivo: breakeven non applicato")
            return
        pnl_pct = portfolio.unrealized_pnl_pct
        avg_entry = portfolio.avg_entry_price
        if pnl_pct is None or avg_entry is None:
            return
        if pnl_pct < self._breakeven_trigger_pct:
            return

        orders = portfolio.open_orders
        tp_order = next(
            (o for o in orders if o.get(_ORDER_TYPE) == _TYPE_LIMIT_MAKER), None
        )
        sl_order = next(
            (o for o in orders if o.get(_ORDER_TYPE) == _TYPE_STOP_LOSS_LIMIT), None
        )
        if tp_order is None or sl_order is None:
            return

        tp_list_id = tp_order.get(_ORDER_LIST_ID)
        sl_list_id = sl_order.get(_ORDER_LIST_ID)
        if tp_list_id is None or tp_list_id != sl_list_id:
            return

        try:
            sl_stop_price = float(sl_order[_STOP_PRICE])
        except (KeyError, TypeError, ValueError):
            return
        if sl_stop_price >= avg_entry:
            return

        try:
            qty = float(tp_order[_ORIG_QTY])
            tp_price = float(tp_order[_ORDER_PRICE])
            order_list_id = int(tp_list_id)
        except (KeyError, TypeError, ValueError) as exc:
            self._logger.warning("Breakeven: impossibile leggere i dati OCO: %s", exc)
            return

        try:
            self._exchange_client.cancel_oco(self._symbol, order_list_id)
            self._exchange_client.place_oco_sell(
                symbol=self._symbol,
                quantity=qty,
                tp_price=tp_price,
                sl_stop_price=avg_entry,
            )
            self._logger.info(
                "Breakeven applicato — SL spostato da %.2f a %.2f (avg_entry), "
                "unrealized_pnl_pct=%.2f%%",
                sl_stop_price,
                avg_entry,
                pnl_pct,
            )
            fresh = self._exchange_client.get_portfolio_state(self._symbol)
            portfolio.open_orders = fresh.open_orders
        except Exception as exc:
            self._logger.warning(
                "Breakeven: operazione fallita, ciclo prosegue: %s", exc,
            )

    def is_oco_review_required(self, portfolio: PortfolioState) -> bool:
        """Restituisce True se almeno un ordine OCO è aperto da >= oco_review_interval_hours."""
        for order in portfolio.open_orders:
            list_id = order.get(_ORDER_LIST_ID, -1)
            age = order.get(_AGE_HOURS, 0.0)
            if list_id != -1 and float(age) >= self._oco_review_interval_hours:
                return True
        return False
