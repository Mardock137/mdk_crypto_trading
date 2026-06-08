from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from src.core.contracts import MarketDataSnapshot, PortfolioState
from src.core.position_manager import PositionManager
from src.utils.memory_manager import MemoryManager


def _make_position_manager(
    exchange_client: MagicMock | None = None,
    memory_manager: MemoryManager | None = None,
    kill_switch: bool = False,
    breakeven_trigger_pct: float = 2.0,
    oco_review_interval_hours: float = 24.0,
    symbol: str = "BTCUSDC",
) -> PositionManager:
    return PositionManager(
        symbol=symbol,
        exchange_client=exchange_client or MagicMock(),
        memory_manager=memory_manager or MagicMock(spec=MemoryManager),
        kill_switch=kill_switch,
        breakeven_trigger_pct=breakeven_trigger_pct,
        oco_review_interval_hours=oco_review_interval_hours,
        logger=logging.getLogger("mdk_crypto_trading.test_position_manager"),
    )


# ---------- Augment portfolio ----------


def test_augment_portfolio_populates_avg_entry_and_unrealized_pnl() -> None:
    """Se c'e posizione aperta e prezzo corrente, popola i due nuovi campi."""
    portfolio = PortfolioState(
        usdc_balance=500.0,
        usdc_balance_total=500.0,
        usdc_value=500.0,
        portfolio_qty_free=0.005,
        portfolio_qty_total=0.005,
    )
    market_data = MarketDataSnapshot(symbol="BTCUSDC", price=88000.0)

    mock_memory = MagicMock(spec=MemoryManager)
    mock_memory.compute_open_position.return_value = {
        "open_qty": 0.005,
        "avg_entry_price": 80000.0,
    }

    pm = _make_position_manager(memory_manager=mock_memory)
    pm.augment_portfolio_with_open_position(market_data, portfolio)

    assert portfolio.avg_entry_price == pytest.approx(80000.0)
    # (88000 - 80000) / 80000 * 100 = 10%
    assert portfolio.unrealized_pnl_pct == pytest.approx(10.0)
    # (88000 - 80000) * 0.005 = 40.0 USDC
    assert portfolio.unrealized_pnl_usdc == pytest.approx(40.0)


def test_augment_portfolio_leaves_fields_none_without_open_position() -> None:
    """Se non c'e posizione aperta (qty totale 0), i nuovi campi restano a None."""
    portfolio = PortfolioState(
        usdc_balance=1000.0,
        usdc_balance_total=1000.0,
        usdc_value=1000.0,
        portfolio_qty_free=0.0,
        portfolio_qty_total=0.0,
    )
    market_data = MarketDataSnapshot(symbol="BTCUSDC", price=80000.0)

    mock_memory = MagicMock(spec=MemoryManager)
    pm = _make_position_manager(memory_manager=mock_memory)
    pm.augment_portfolio_with_open_position(market_data, portfolio)

    assert portfolio.avg_entry_price is None
    assert portfolio.unrealized_pnl_pct is None
    assert portfolio.unrealized_pnl_usdc is None
    mock_memory.compute_open_position.assert_not_called()


def test_augment_portfolio_unrealized_pnl_usdc_negative_when_in_loss() -> None:
    """unrealized_pnl_usdc deve essere negativo quando price < avg_entry_price."""
    portfolio = PortfolioState(
        usdc_balance=500.0,
        usdc_balance_total=500.0,
        usdc_value=450.0,
        portfolio_qty_free=0.01,
        portfolio_qty_total=0.01,
    )
    market_data = MarketDataSnapshot(symbol="BTCUSDC", price=90000.0)

    mock_memory = MagicMock(spec=MemoryManager)
    mock_memory.compute_open_position.return_value = {
        "open_qty": 0.01,
        "avg_entry_price": 95000.0,
    }

    pm = _make_position_manager(memory_manager=mock_memory)
    pm.augment_portfolio_with_open_position(market_data, portfolio)

    # (90000 - 95000) / 95000 * 100 ≈ -5.2632%
    assert portfolio.unrealized_pnl_pct == pytest.approx(-5.2632, rel=1e-3)
    # (90000 - 95000) * 0.01 = -50.0 USDC
    assert portfolio.unrealized_pnl_usdc == pytest.approx(-50.0)


def test_augment_portfolio_pnl_usdc_uses_open_qty_not_qty_total() -> None:
    """unrealized_pnl_usdc deve usare open_qty FIFO, non portfolio_qty_total."""
    portfolio = PortfolioState(
        usdc_balance=500.0,
        usdc_balance_total=500.0,
        usdc_value=500.0,
        portfolio_qty_free=0.010,
        portfolio_qty_total=0.010,  # saldo exchange: 0.010
    )
    market_data = MarketDataSnapshot(symbol="BTCUSDC", price=90000.0)

    mock_memory = MagicMock(spec=MemoryManager)
    mock_memory.compute_open_position.return_value = {
        "open_qty": 0.005,          # FIFO traccia solo 0.005 (divergenza)
        "avg_entry_price": 80000.0,
    }

    pm = _make_position_manager(memory_manager=mock_memory)
    pm.augment_portfolio_with_open_position(market_data, portfolio)

    # P&L % non dipende dalla quantità: invariato
    assert portfolio.unrealized_pnl_pct == pytest.approx(12.5)
    # P&L USDC deve usare open_qty=0.005, NON qty_total=0.010
    # (90000 - 80000) * 0.005 = 50.0 USDC
    assert portfolio.unrealized_pnl_usdc == pytest.approx(50.0)


def test_augment_portfolio_logs_warning_on_qty_divergence(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Quando open_qty e qty_total divergono oltre tolleranza viene emesso un WARNING."""
    portfolio = PortfolioState(
        usdc_balance=500.0,
        usdc_balance_total=500.0,
        usdc_value=500.0,
        portfolio_qty_free=0.010,
        portfolio_qty_total=0.010,
    )
    market_data = MarketDataSnapshot(symbol="BTCUSDC", price=90000.0)

    mock_memory = MagicMock(spec=MemoryManager)
    mock_memory.compute_open_position.return_value = {
        "open_qty": 0.005,
        "avg_entry_price": 80000.0,
    }

    pm = _make_position_manager(memory_manager=mock_memory)

    with caplog.at_level(logging.WARNING, logger="mdk_crypto_trading"):
        pm.augment_portfolio_with_open_position(market_data, portfolio)

    assert any("Divergenza" in r.message for r in caplog.records)


# ---------- Breakeven automatico ----------


def _make_oco_portfolio(
    *,
    pnl_pct: float,
    avg_entry: float,
    sl_stop_price: float,
    order_list_id: int = 99,
    tp_price: float = 100000.0,
    qty: float = 0.005,
) -> PortfolioState:
    """Portfolio con OCO attivo e unrealized_pnl_pct valorizzato."""
    portfolio = PortfolioState(
        usdc_balance=500.0,
        usdc_balance_total=500.0,
        usdc_value=500.0,
        portfolio_qty_free=qty,
        portfolio_qty_total=qty,
    )
    portfolio.unrealized_pnl_pct = pnl_pct
    portfolio.avg_entry_price = avg_entry
    portfolio.open_orders = [
        {
            "type": "LIMIT_MAKER",
            "orderListId": order_list_id,
            "price": str(tp_price),
            "origQty": str(qty),
            "stopPrice": "0",
        },
        {
            "type": "STOP_LOSS_LIMIT",
            "orderListId": order_list_id,
            "price": str(sl_stop_price * 0.995),
            "origQty": str(qty),
            "stopPrice": str(sl_stop_price),
        },
    ]
    return portfolio


def test_breakeven_triggers_when_all_conditions_met() -> None:
    """Con tutte le condizioni soddisfatte, cancella l'OCO e ne piazza uno nuovo con SL a breakeven."""
    mock_exchange = MagicMock()
    portfolio = _make_oco_portfolio(
        pnl_pct=2.5,
        avg_entry=90000.0,
        sl_stop_price=85000.0,
    )
    mock_exchange.get_portfolio_state.return_value = PortfolioState(
        usdc_balance=500.0,
        usdc_balance_total=500.0,
        usdc_value=500.0,
        portfolio_qty_free=0.005,
        portfolio_qty_total=0.005,
        open_orders=[],
    )

    pm = _make_position_manager(exchange_client=mock_exchange)
    pm.maybe_apply_breakeven(portfolio)

    mock_exchange.cancel_oco.assert_called_once_with("BTCUSDC", 99)
    mock_exchange.place_oco_sell.assert_called_once_with(
        symbol="BTCUSDC",
        quantity=0.005,
        tp_price=100000.0,
        sl_stop_price=90000.0,  # avg_entry
    )


def test_breakeven_not_triggered_when_pnl_is_none() -> None:
    """Se unrealized_pnl_pct è None il breakeven non si attiva."""
    mock_exchange = MagicMock()
    portfolio = _make_oco_portfolio(pnl_pct=3.0, avg_entry=90000.0, sl_stop_price=85000.0)
    portfolio.unrealized_pnl_pct = None

    pm = _make_position_manager(exchange_client=mock_exchange)
    pm.maybe_apply_breakeven(portfolio)

    mock_exchange.cancel_oco.assert_not_called()


def test_breakeven_not_triggered_below_threshold() -> None:
    """Se unrealized_pnl_pct < breakeven_trigger_pct il breakeven non si attiva."""
    mock_exchange = MagicMock()
    portfolio = _make_oco_portfolio(pnl_pct=1.5, avg_entry=90000.0, sl_stop_price=85000.0)

    pm = _make_position_manager(exchange_client=mock_exchange)
    pm.maybe_apply_breakeven(portfolio)

    mock_exchange.cancel_oco.assert_not_called()


def test_breakeven_not_triggered_without_oco() -> None:
    """Se non c'è OCO attivo (nessun LIMIT_MAKER/STOP_LOSS_LIMIT) il breakeven non si attiva."""
    mock_exchange = MagicMock()
    portfolio = PortfolioState(
        usdc_balance=500.0,
        usdc_balance_total=500.0,
        usdc_value=500.0,
        portfolio_qty_free=0.005,
        portfolio_qty_total=0.005,
        open_orders=[],
    )
    portfolio.unrealized_pnl_pct = 3.0
    portfolio.avg_entry_price = 90000.0

    pm = _make_position_manager(exchange_client=mock_exchange)
    pm.maybe_apply_breakeven(portfolio)

    mock_exchange.cancel_oco.assert_not_called()


def test_breakeven_not_triggered_when_sl_already_above_entry() -> None:
    """Se lo SL è già >= avg_entry_price il breakeven è già attivo, non fa nulla."""
    mock_exchange = MagicMock()
    portfolio = _make_oco_portfolio(
        pnl_pct=3.0,
        avg_entry=90000.0,
        sl_stop_price=90500.0,  # già sopra avg_entry
    )

    pm = _make_position_manager(exchange_client=mock_exchange)
    pm.maybe_apply_breakeven(portfolio)

    mock_exchange.cancel_oco.assert_not_called()


def test_breakeven_not_triggered_when_sl_equals_entry() -> None:
    """Se lo SL è esattamente uguale ad avg_entry_price il breakeven è già attivo."""
    mock_exchange = MagicMock()
    portfolio = _make_oco_portfolio(
        pnl_pct=3.0,
        avg_entry=90000.0,
        sl_stop_price=90000.0,  # uguale ad avg_entry
    )

    pm = _make_position_manager(exchange_client=mock_exchange)
    pm.maybe_apply_breakeven(portfolio)

    mock_exchange.cancel_oco.assert_not_called()


def test_breakeven_exception_does_not_block_cycle() -> None:
    """Se cancel_oco lancia un'eccezione, il breakeven logga un warning e il ciclo prosegue."""
    mock_exchange = MagicMock()
    mock_exchange.cancel_oco.side_effect = RuntimeError("Binance down")
    portfolio = _make_oco_portfolio(
        pnl_pct=2.5,
        avg_entry=90000.0,
        sl_stop_price=85000.0,
    )

    pm = _make_position_manager(exchange_client=mock_exchange)
    pm.maybe_apply_breakeven(portfolio)  # non deve sollevare

    mock_exchange.cancel_oco.assert_called_once()
    mock_exchange.place_oco_sell.assert_not_called()


def test_breakeven_not_triggered_when_kill_switch_active() -> None:
    """Con kill switch attivo, cancel_oco e place_oco_sell non vengono chiamati."""
    mock_exchange = MagicMock()
    portfolio = _make_oco_portfolio(
        pnl_pct=2.5,
        avg_entry=90000.0,
        sl_stop_price=85000.0,
    )

    pm = _make_position_manager(exchange_client=mock_exchange, kill_switch=True)
    pm.maybe_apply_breakeven(portfolio)

    mock_exchange.cancel_oco.assert_not_called()
    mock_exchange.place_oco_sell.assert_not_called()


# ---------- OCO review periodica ----------


def _make_portfolio_with_orders(orders: list[dict]) -> PortfolioState:
    return PortfolioState(
        usdc_balance=500.0,
        usdc_balance_total=500.0,
        usdc_value=500.0,
        portfolio_qty_free=0.005,
        portfolio_qty_total=0.005,
        open_orders=orders,
    )


def test_is_oco_review_required_true_when_oco_old_enough() -> None:
    """Restituisce True se un ordine OCO ha age_hours >= soglia."""
    pm = _make_position_manager(oco_review_interval_hours=24.0)
    portfolio = _make_portfolio_with_orders([
        {"type": "LIMIT_MAKER", "orderListId": 42, "age_hours": 25.0},
        {"type": "STOP_LOSS_LIMIT", "orderListId": 42, "age_hours": 25.0},
    ])
    assert pm.is_oco_review_required(portfolio) is True


def test_is_oco_review_required_false_when_oco_below_threshold() -> None:
    """Restituisce False se l'OCO è sotto soglia."""
    pm = _make_position_manager(oco_review_interval_hours=24.0)
    portfolio = _make_portfolio_with_orders([
        {"type": "LIMIT_MAKER", "orderListId": 42, "age_hours": 10.0},
    ])
    assert pm.is_oco_review_required(portfolio) is False


def test_is_oco_review_required_false_when_no_oco_order() -> None:
    """Restituisce False se non ci sono ordini OCO (orderListId == -1)."""
    pm = _make_position_manager(oco_review_interval_hours=24.0)
    portfolio = _make_portfolio_with_orders([
        {"type": "LIMIT", "orderListId": -1, "age_hours": 30.0},
    ])
    assert pm.is_oco_review_required(portfolio) is False


def test_is_oco_review_required_false_when_no_orders() -> None:
    """Restituisce False se open_orders è vuoto."""
    pm = _make_position_manager()
    portfolio = _make_portfolio_with_orders([])
    assert pm.is_oco_review_required(portfolio) is False
