from __future__ import annotations

from pathlib import Path

import pytest

from src.core.contracts import (
    ExecutionReport,
    ExecutionStatus,
    MarketAnalysis,
    MarketBias,
    OrderType,
    RiskAssessment,
    RiskDecision,
    SuggestedAction,
    TradeAction,
    TradeProposal,
    TradeProposalDetails,
    TradingCycleResult,
)
from src.utils.memory_manager import MemoryManager


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_result(
    action: TradeAction = TradeAction.BUY,
    execution_status: ExecutionStatus = ExecutionStatus.EXECUTED,
    confidence: float = 0.75,
    quantity: float | None = 0.001,
) -> TradingCycleResult:
    return TradingCycleResult(
        market_analysis=MarketAnalysis(
            market_bias=MarketBias.BULLISH,
            signal_strength=0.8,
            confidence=0.7,
            summary="Test analysis",
            suggested_action=SuggestedAction.LONG_BIAS,
        ),
        trade_proposal=TradeProposal(
            action=action,
            order_type=OrderType.MARKET,
            confidence=confidence,
            reason="Test reason",
            details=TradeProposalDetails(quantity=quantity),
        ),
        risk_assessment=RiskAssessment(
            risk_decision=RiskDecision.APPROVE,
            confidence=0.9,
            reason="Test risk",
        ),
        execution_report=ExecutionReport(
            execution_status=execution_status,
            executed_action=action,
            order_type=OrderType.MARKET,
            reason="Test execution",
        ),
    )


# ------------------------------------------------------------------
# _symbol_path — whitelist regex
# ------------------------------------------------------------------


def test_symbol_path_rejects_path_traversal(tmp_path: Path) -> None:
    """_symbol_path deve rifiutare simboli con caratteri non ammessi (path traversal)."""
    mm = MemoryManager(memory_dir=tmp_path)
    with pytest.raises(ValueError, match="Symbol non valido"):
        mm._symbol_path("../secrets")


def test_symbol_path_rejects_lowercase(tmp_path: Path) -> None:
    """_symbol_path deve rifiutare simboli con lettere minuscole."""
    mm = MemoryManager(memory_dir=tmp_path)
    with pytest.raises(ValueError, match="Symbol non valido"):
        mm._symbol_path("btcusdc")


def test_symbol_path_accepts_valid_symbol(tmp_path: Path) -> None:
    """_symbol_path deve accettare simboli di trading validi."""
    mm = MemoryManager(memory_dir=tmp_path)
    path = mm._symbol_path("BTCUSDC")
    assert path == tmp_path / "BTCUSDC.jsonl"


# ------------------------------------------------------------------
# save_cycle
# ------------------------------------------------------------------


def test_save_cycle_creates_jsonl_file(tmp_path: Path) -> None:
    """save_cycle deve creare il file JSONL per il simbolo."""
    mm = MemoryManager(memory_dir=tmp_path)
    mm.save_cycle(symbol="BTCUSDC", result=_make_result(), current_price=67000.0)

    assert (tmp_path / "BTCUSDC.jsonl").exists()


def test_save_cycle_writes_expected_fields(tmp_path: Path) -> None:
    """save_cycle deve scrivere tutti i campi attesi nel record JSONL."""
    import json

    mm = MemoryManager(memory_dir=tmp_path)
    mm.save_cycle(symbol="BTCUSDC", result=_make_result(), current_price=67000.0)

    lines = (tmp_path / "BTCUSDC.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    record = json.loads(lines[0])
    assert record["action"] == "BUY"
    assert record["order_type"] == "MARKET"
    assert record["execution_status"] == "EXECUTED"
    assert record["risk_decision"] == "APPROVE"
    assert record["market_bias"] == "BULLISH"
    assert record["price"] == pytest.approx(67000.0)
    assert "timestamp" in record


# ------------------------------------------------------------------
# get_memory
# ------------------------------------------------------------------


def test_get_memory_returns_last_10(tmp_path: Path) -> None:
    """get_memory deve ritornare le ultime 10 decisioni anche se ce ne sono 15."""
    mm = MemoryManager(memory_dir=tmp_path)

    for i in range(15):
        mm.save_cycle(
            symbol="BTCUSDC",
            result=_make_result(confidence=float(i) / 100),
            current_price=float(60000 + i),
        )

    records = mm.get_memory("BTCUSDC")
    assert len(records) == 10
    assert records[0]["price"] == pytest.approx(60005.0)
    assert records[-1]["price"] == pytest.approx(60014.0)


def test_get_memory_returns_empty_for_missing_symbol(tmp_path: Path) -> None:
    """get_memory deve ritornare lista vuota se il simbolo non ha file."""
    mm = MemoryManager(memory_dir=tmp_path)
    assert mm.get_memory("ETHUSDC") == []


# ------------------------------------------------------------------
# get_recent_performance
# ------------------------------------------------------------------


def test_get_recent_performance_buy_has_no_pnl_fields(tmp_path: Path) -> None:
    """get_recent_performance: i record BUY non devono avere realized_pnl o pnl_pct."""
    mm = MemoryManager(memory_dir=tmp_path)
    mm.save_cycle(symbol="BTCUSDC", result=_make_result(action=TradeAction.BUY), current_price=65000.0)

    perf = mm.get_recent_performance("BTCUSDC")
    assert len(perf) == 1
    assert perf[0]["action"] == "BUY"
    assert "realized_pnl" not in perf[0]
    assert "pnl_pct" not in perf[0]


def test_get_recent_performance_sell_has_pnl_fields(tmp_path: Path) -> None:
    """get_recent_performance: una SELL dopo un BUY deve avere realized_pnl e pnl_pct."""
    mm = MemoryManager(memory_dir=tmp_path)
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, quantity=0.001),
        current_price=80000.0,
    )
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.SELL, quantity=0.001),
        current_price=83000.0,
    )

    perf = mm.get_recent_performance("BTCUSDC")
    sell_entry = next(e for e in perf if e["action"] == "SELL")
    assert "realized_pnl" in sell_entry
    assert "pnl_pct" in sell_entry
    assert sell_entry["realized_pnl"] == pytest.approx(3.0, rel=1e-3)
    assert sell_entry["pnl_pct"] == pytest.approx(3.75, rel=1e-3)


def test_get_recent_performance_includes_quantity(tmp_path: Path) -> None:
    """get_recent_performance deve includere il campo quantity nei record."""
    mm = MemoryManager(memory_dir=tmp_path)
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, quantity=0.002),
        current_price=70000.0,
    )

    perf = mm.get_recent_performance("BTCUSDC")
    assert perf[0]["quantity"] == pytest.approx(0.002)


def test_get_recent_performance_hold_has_no_pnl_fields(tmp_path: Path) -> None:
    """get_recent_performance: i record HOLD non devono avere realized_pnl o pnl_pct."""
    mm = MemoryManager(memory_dir=tmp_path)
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.HOLD, execution_status=ExecutionStatus.NOT_EXECUTED),
        current_price=None,
    )

    perf = mm.get_recent_performance("BTCUSDC")
    assert perf[0]["action"] == "HOLD"
    assert "realized_pnl" not in perf[0]
    assert "pnl_pct" not in perf[0]


# ------------------------------------------------------------------
# get_performance_summary — casi base
# ------------------------------------------------------------------


def test_get_performance_summary_without_sell_returns_empty(tmp_path: Path) -> None:
    """get_performance_summary deve ritornare stringa vuota senza SELL eseguiti."""
    mm = MemoryManager(memory_dir=tmp_path)
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY),
        current_price=60000.0,
    )

    assert mm.get_performance_summary("BTCUSDC") == ""


def test_get_performance_summary_no_data_returns_empty(tmp_path: Path) -> None:
    """get_performance_summary deve ritornare stringa vuota senza dati."""
    mm = MemoryManager(memory_dir=tmp_path)
    assert mm.get_performance_summary("BTCUSDC") == ""


def test_get_performance_summary_profit(tmp_path: Path) -> None:
    """Scenario base: BUY a 80000, SELL a 83000 → profitto."""
    mm = MemoryManager(memory_dir=tmp_path)
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, quantity=0.001),
        current_price=80000.0,
    )
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.SELL, quantity=0.001),
        current_price=83000.0,
    )

    summary = mm.get_performance_summary("BTCUSDC")
    assert "1 in profitto" in summary
    assert "0 in perdita" in summary
    assert "+3.75%" in summary or "+3.8%" in summary
    assert "+3.00 USDC" in summary or "+3.0 USDC" in summary


def test_get_performance_summary_loss(tmp_path: Path) -> None:
    """Scenario base: BUY a 85000, SELL a 83000 → perdita."""
    mm = MemoryManager(memory_dir=tmp_path)
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, quantity=0.001),
        current_price=85000.0,
    )
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.SELL, quantity=0.001),
        current_price=83000.0,
    )

    summary = mm.get_performance_summary("BTCUSDC")
    assert "0 in profitto" in summary
    assert "1 in perdita" in summary
    assert "-" in summary


def test_get_performance_summary_contains_fifo_label(tmp_path: Path) -> None:
    """get_performance_summary deve contenere l'etichetta FIFO nel testo."""
    mm = MemoryManager(memory_dir=tmp_path)
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, quantity=0.001),
        current_price=80000.0,
    )
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.SELL, quantity=0.001),
        current_price=82000.0,
    )

    summary = mm.get_performance_summary("BTCUSDC")
    assert "FIFO" in summary


# ------------------------------------------------------------------
# compute_fifo_trades — scenari FIFO dettagliati
# ------------------------------------------------------------------


def test_fifo_multiple_buys_uses_oldest_first(tmp_path: Path) -> None:
    """FIFO: con due BUY a prezzi diversi, la SELL consuma il piu vecchio."""
    mm = MemoryManager(memory_dir=tmp_path)
    # BUY 0.001 @ 80000 (primo)
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, quantity=0.001),
        current_price=80000.0,
    )
    # BUY 0.001 @ 85000 (secondo)
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, quantity=0.001),
        current_price=85000.0,
    )
    # SELL 0.001 @ 83000 → deve consumare il lotto a 80000 (+3.75%)
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.SELL, quantity=0.001),
        current_price=83000.0,
    )

    trades = mm.compute_fifo_trades("BTCUSDC")
    assert len(trades) == 1
    assert trades[0]["avg_cost_basis"] == pytest.approx(80000.0)
    assert trades[0]["realized_pnl"] == pytest.approx(3.0, rel=1e-3)
    assert trades[0]["pnl_pct"] == pytest.approx(3.75, rel=1e-3)


def test_fifo_partial_sell_leaves_residual_lot(tmp_path: Path) -> None:
    """FIFO: una vendita parziale deve lasciare la quantita residua nel lotto."""
    mm = MemoryManager(memory_dir=tmp_path)
    # BUY 0.003 @ 80000
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, quantity=0.003),
        current_price=80000.0,
    )
    # SELL 0.001 @ 84000 → consuma solo 0.001 del lotto da 0.003
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.SELL, quantity=0.001),
        current_price=84000.0,
    )
    # SELL 0.001 @ 82000 → consuma un altro 0.001 dallo stesso lotto
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.SELL, quantity=0.001),
        current_price=82000.0,
    )

    trades = mm.compute_fifo_trades("BTCUSDC")
    assert len(trades) == 2
    # Prima SELL: (84000 - 80000) * 0.001 = +4.0
    assert trades[0]["realized_pnl"] == pytest.approx(4.0, rel=1e-3)
    # Seconda SELL: (82000 - 80000) * 0.001 = +2.0
    assert trades[1]["realized_pnl"] == pytest.approx(2.0, rel=1e-3)


def test_fifo_sell_across_multiple_lots(tmp_path: Path) -> None:
    """FIFO: una SELL che attraversa piu lotti usa il costo medio ponderato."""
    mm = MemoryManager(memory_dir=tmp_path)
    # BUY 0.001 @ 80000
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, quantity=0.001),
        current_price=80000.0,
    )
    # BUY 0.001 @ 90000
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, quantity=0.001),
        current_price=90000.0,
    )
    # SELL 0.002 @ 88000 → consuma entrambi i lotti
    # costo medio = (0.001*80000 + 0.001*90000) / 0.002 = 85000
    # P&L = 0.002 * (88000 - 85000) = +6.0
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.SELL, quantity=0.002),
        current_price=88000.0,
    )

    trades = mm.compute_fifo_trades("BTCUSDC")
    assert len(trades) == 1
    assert trades[0]["avg_cost_basis"] == pytest.approx(85000.0, rel=1e-6)
    assert trades[0]["realized_pnl"] == pytest.approx(6.0, rel=1e-3)
    assert trades[0]["quantity"] == pytest.approx(0.002, rel=1e-6)


def test_fifo_sell_without_buy_is_ignored(tmp_path: Path) -> None:
    """FIFO: una SELL senza BUY precedenti non deve produrre nessuna trade."""
    mm = MemoryManager(memory_dir=tmp_path)
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.SELL, quantity=0.001),
        current_price=83000.0,
    )

    trades = mm.compute_fifo_trades("BTCUSDC")
    assert trades == []


def test_fifo_ignores_records_with_none_quantity(tmp_path: Path) -> None:
    """FIFO: i record con quantity None devono essere ignorati."""
    mm = MemoryManager(memory_dir=tmp_path)
    # BUY con quantity None
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, quantity=None),
        current_price=80000.0,
    )
    # SELL normale → nessun lotto disponibile, viene ignorata
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.SELL, quantity=0.001),
        current_price=83000.0,
    )

    trades = mm.compute_fifo_trades("BTCUSDC")
    assert trades == []


def test_fifo_ignores_non_executed_records(tmp_path: Path) -> None:
    """FIFO: i record non EXECUTED non devono influenzare la coda di lotti."""
    mm = MemoryManager(memory_dir=tmp_path)
    # BUY FAILED → non deve entrare in coda
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, execution_status=ExecutionStatus.FAILED, quantity=0.001),
        current_price=80000.0,
    )
    # SELL EXECUTED → nessun lotto disponibile
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.SELL, quantity=0.001),
        current_price=83000.0,
    )

    trades = mm.compute_fifo_trades("BTCUSDC")
    assert trades == []


def test_fifo_multiple_sell_cycles_accumulate(tmp_path: Path) -> None:
    """FIFO: piu cicli buy/sell consecutivi devono accumularsi correttamente."""
    mm = MemoryManager(memory_dir=tmp_path)

    # Ciclo 1: BUY @ 80000, SELL @ 82000 → profitto
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, quantity=0.001),
        current_price=80000.0,
    )
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.SELL, quantity=0.001),
        current_price=82000.0,
    )
    # Ciclo 2: BUY @ 85000, SELL @ 83000 → perdita
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, quantity=0.001),
        current_price=85000.0,
    )
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.SELL, quantity=0.001),
        current_price=83000.0,
    )

    trades = mm.compute_fifo_trades("BTCUSDC")
    assert len(trades) == 2
    assert trades[0]["realized_pnl"] == pytest.approx(2.0, rel=1e-3)
    assert trades[1]["realized_pnl"] == pytest.approx(-2.0, rel=1e-3)

    summary = mm.get_performance_summary("BTCUSDC")
    assert "1 in profitto" in summary
    assert "1 in perdita" in summary


# ------------------------------------------------------------------
# compute_open_position
# ------------------------------------------------------------------


def test_compute_open_position_returns_none_when_no_buys(tmp_path: Path) -> None:
    """Senza BUY eseguiti, non c'e posizione aperta."""
    mm = MemoryManager(memory_dir=tmp_path)
    assert mm.compute_open_position("BTCUSDC") is None


def test_compute_open_position_returns_none_after_full_sell(tmp_path: Path) -> None:
    """Dopo che tutti i lotti BUY sono stati venduti, la posizione e chiusa."""
    mm = MemoryManager(memory_dir=tmp_path)
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, quantity=0.001),
        current_price=80000.0,
    )
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.SELL, quantity=0.001),
        current_price=82000.0,
    )

    assert mm.compute_open_position("BTCUSDC") is None


def test_compute_open_position_single_buy(tmp_path: Path) -> None:
    """Con un solo BUY, la posizione aperta corrisponde a quel lotto."""
    mm = MemoryManager(memory_dir=tmp_path)
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, quantity=0.002),
        current_price=80000.0,
    )

    pos = mm.compute_open_position("BTCUSDC")
    assert pos is not None
    assert pos["open_qty"] == pytest.approx(0.002, rel=1e-6)
    assert pos["avg_entry_price"] == pytest.approx(80000.0, rel=1e-6)


def test_compute_open_position_after_partial_sell(tmp_path: Path) -> None:
    """Dopo SELL parziale, resta la quantita residua del lotto al prezzo originale."""
    mm = MemoryManager(memory_dir=tmp_path)
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, quantity=0.003),
        current_price=80000.0,
    )
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.SELL, quantity=0.001),
        current_price=84000.0,
    )

    pos = mm.compute_open_position("BTCUSDC")
    assert pos is not None
    assert pos["open_qty"] == pytest.approx(0.002, rel=1e-6)
    assert pos["avg_entry_price"] == pytest.approx(80000.0, rel=1e-6)


def test_compute_open_position_weighted_avg_multiple_lots(tmp_path: Path) -> None:
    """Con piu lotti BUY aperti, il prezzo medio e la media ponderata."""
    mm = MemoryManager(memory_dir=tmp_path)
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, quantity=0.001),
        current_price=80000.0,
    )
    mm.save_cycle(
        symbol="BTCUSDC",
        result=_make_result(action=TradeAction.BUY, quantity=0.001),
        current_price=90000.0,
    )

    pos = mm.compute_open_position("BTCUSDC")
    assert pos is not None
    assert pos["open_qty"] == pytest.approx(0.002, rel=1e-6)
    assert pos["avg_entry_price"] == pytest.approx(85000.0, rel=1e-6)
