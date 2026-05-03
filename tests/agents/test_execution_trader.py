"""Test per ExecutionTraderAgent.run() con mock dell'exchange client."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.agents.execution_trader import ExecutionTraderAgent
from src.core.contracts import (
    ExecutionInput,
    ExecutionStatus,
    InvestmentMandate,
    OrderSide,
    OrderType,
    PortfolioState,
    RiskAssessment,
    RiskDecision,
    TradeAction,
    TradeProposal,
    TradeProposalDetails,
)

_DEFAULT_PORTFOLIO = PortfolioState(
    usdc_balance=1000.0,
    usdc_balance_total=1000.0,
    usdc_value=1000.0,
    portfolio_qty_free=0.0,
    portfolio_qty_total=0.0,
)

_DEFAULT_MANDATE = InvestmentMandate(
    max_drawdown_pct=15.0,
    horizon="Intraday to swing",
    max_position_pct=70.0,
)


def _make_input(
    proposal: TradeProposal,
    risk: RiskAssessment,
    portfolio: PortfolioState = _DEFAULT_PORTFOLIO,
    mandate: InvestmentMandate = _DEFAULT_MANDATE,
    current_price: float | None = 100_000.0,
    max_order_notional_usdc: float = 100_000.0,
) -> ExecutionInput:
    return ExecutionInput(
        symbol="BTCUSDC",
        proposal=proposal,
        risk_assessment=risk,
        portfolio=portfolio,
        mandate=mandate,
        max_order_notional_usdc=max_order_notional_usdc,
        current_price=current_price,
    )


APPROVED = RiskAssessment(
    risk_decision=RiskDecision.APPROVE,
    confidence=0.9,
    reason="Ok",
)

BLOCKED = RiskAssessment(
    risk_decision=RiskDecision.BLOCK,
    confidence=0.95,
    reason="Troppo rischioso",
)


# --- Kill switch attivo ---

def test_kill_switch_blocks_approved_buy() -> None:
    mock_exchange = MagicMock()
    proposal = TradeProposal(
        action=TradeAction.BUY,
        order_type=OrderType.MARKET,
        confidence=0.85,
        reason="segnale forte",
        details=TradeProposalDetails(quantity=0.001),
    )
    agent = ExecutionTraderAgent(exchange_client=mock_exchange, kill_switch=True)
    report = agent.run(_make_input(proposal, APPROVED))

    assert report.execution_status is ExecutionStatus.NOT_EXECUTED
    assert "Kill switch" in report.reason
    mock_exchange.place_market_order.assert_not_called()


# --- Proposta non approvata ---

def test_not_approved_returns_not_executed() -> None:
    proposal = TradeProposal(
        action=TradeAction.BUY,
        order_type=OrderType.MARKET,
        confidence=0.8,
        reason="segnale forte",
        details=TradeProposalDetails(quantity=0.001),
    )
    agent = ExecutionTraderAgent(exchange_client=MagicMock())
    report = agent.run(_make_input(proposal, BLOCKED))

    assert report.execution_status is ExecutionStatus.NOT_EXECUTED
    assert "non approvata" in report.reason


# --- HOLD approvata ---

def test_hold_approved_returns_not_executed() -> None:
    proposal = TradeProposal(
        action=TradeAction.HOLD,
        order_type=OrderType.NONE,
        confidence=0.6,
        reason="mercato incerto",
    )
    agent = ExecutionTraderAgent(exchange_client=MagicMock())
    report = agent.run(_make_input(proposal, APPROVED))

    assert report.execution_status is ExecutionStatus.NOT_EXECUTED
    assert report.executed_action is TradeAction.HOLD


# --- BUY MARKET approvata ---

def test_buy_market_calls_place_market_order() -> None:
    mock_exchange = MagicMock()
    mock_exchange.place_market_order.return_value = {"orderId": "111"}

    proposal = TradeProposal(
        action=TradeAction.BUY,
        order_type=OrderType.MARKET,
        confidence=0.85,
        reason="long bias",
        details=TradeProposalDetails(quantity=0.001),
    )
    agent = ExecutionTraderAgent(exchange_client=mock_exchange)
    report = agent.run(_make_input(proposal, APPROVED))

    assert report.execution_status is ExecutionStatus.EXECUTED
    mock_exchange.place_market_order.assert_called_once_with(
        "BTCUSDC", "BUY", 0.001,
    )
    assert report.execution_details == {"orderId": "111"}


# --- SELL LIMIT approvata ---

def test_sell_limit_calls_place_limit_order() -> None:
    mock_exchange = MagicMock()
    mock_exchange.place_limit_order.return_value = {"orderId": "222"}

    proposal = TradeProposal(
        action=TradeAction.SELL,
        order_type=OrderType.LIMIT,
        confidence=0.76,
        reason="resistenza vicina",
        details=TradeProposalDetails(quantity=0.001, price=98500.0),
    )
    agent = ExecutionTraderAgent(exchange_client=mock_exchange)
    report = agent.run(_make_input(proposal, APPROVED))

    assert report.execution_status is ExecutionStatus.EXECUTED
    mock_exchange.place_limit_order.assert_called_once_with(
        "BTCUSDC", "SELL", 0.001, 98500.0,
    )


# --- CANCEL_AND_REPLACE approvata ---

def test_cancel_and_replace_calls_cancel_then_limit() -> None:
    mock_exchange = MagicMock()
    mock_exchange.cancel_order.return_value = {"status": "CANCELED"}
    mock_exchange.place_limit_order.return_value = {"orderId": "333"}

    proposal = TradeProposal(
        action=TradeAction.CANCEL_AND_REPLACE_ORDER,
        order_type=OrderType.LIMIT,
        confidence=0.71,
        reason="prezzo migliorato",
        details=TradeProposalDetails(
            order_id="999", side=OrderSide.BUY, quantity=0.001, price=97250.0,
        ),
    )
    portfolio_with_open_order = PortfolioState(
        usdc_balance=1000.0,
        usdc_balance_total=1000.0,
        usdc_value=1000.0,
        portfolio_qty_free=0.0,
        portfolio_qty_total=0.0,
        open_orders=[{"orderId": "999", "clientOrderId": "abc"}],
    )
    agent = ExecutionTraderAgent(exchange_client=mock_exchange)
    report = agent.run(_make_input(proposal, APPROVED, portfolio=portfolio_with_open_order))

    assert report.execution_status is ExecutionStatus.EXECUTED
    mock_exchange.cancel_order.assert_called_once_with("BTCUSDC", "999")
    mock_exchange.place_limit_order.assert_called_once_with(
        "BTCUSDC", "BUY", 0.001, 97250.0,
    )


# --- Validazione input mancante (CR-01) ---

def test_buy_market_without_quantity_returns_failed() -> None:
    proposal = TradeProposal(
        action=TradeAction.BUY,
        order_type=OrderType.MARKET,
        confidence=0.8,
        reason="segnale",
        details=TradeProposalDetails(),
    )
    agent = ExecutionTraderAgent(exchange_client=MagicMock())
    report = agent.run(_make_input(proposal, APPROVED))

    assert report.execution_status is ExecutionStatus.FAILED
    assert "quantity" in report.reason


def test_sell_limit_without_price_returns_failed() -> None:
    proposal = TradeProposal(
        action=TradeAction.SELL,
        order_type=OrderType.LIMIT,
        confidence=0.8,
        reason="segnale",
        details=TradeProposalDetails(quantity=0.001),
    )
    agent = ExecutionTraderAgent(exchange_client=MagicMock())
    report = agent.run(_make_input(proposal, APPROVED))

    assert report.execution_status is ExecutionStatus.FAILED
    assert "price" in report.reason


def test_cancel_replace_without_order_id_returns_failed() -> None:
    """Con order_id=None il guardrail blocca l'operazione prima dell'exchange (NOT_EXECUTED)."""
    proposal = TradeProposal(
        action=TradeAction.CANCEL_AND_REPLACE_ORDER,
        order_type=OrderType.LIMIT,
        confidence=0.7,
        reason="aggiornamento prezzo",
        details=TradeProposalDetails(
            side=OrderSide.BUY, quantity=0.001, price=97000.0,
        ),
    )
    agent = ExecutionTraderAgent(exchange_client=MagicMock())
    report = agent.run(_make_input(proposal, APPROVED))

    assert report.execution_status is ExecutionStatus.NOT_EXECUTED
    assert "order_id" in report.reason


# --- Stato parziale CANCEL_AND_REPLACE (CR-03) ---

def test_cancel_and_replace_partial_failure_returns_failed() -> None:
    mock_exchange = MagicMock()
    mock_exchange.cancel_order.return_value = {"status": "CANCELED"}
    mock_exchange.place_limit_order.side_effect = RuntimeError("API timeout")

    proposal = TradeProposal(
        action=TradeAction.CANCEL_AND_REPLACE_ORDER,
        order_type=OrderType.LIMIT,
        confidence=0.71,
        reason="prezzo migliorato",
        details=TradeProposalDetails(
            order_id="999", side=OrderSide.BUY, quantity=0.001, price=97250.0,
        ),
    )
    portfolio_with_open_order = PortfolioState(
        usdc_balance=1000.0,
        usdc_balance_total=1000.0,
        usdc_value=1000.0,
        portfolio_qty_free=0.0,
        portfolio_qty_total=0.0,
        open_orders=[{"orderId": "999", "clientOrderId": "abc"}],
    )
    agent = ExecutionTraderAgent(exchange_client=mock_exchange)
    report = agent.run(_make_input(proposal, APPROVED, portfolio=portfolio_with_open_order))

    assert report.execution_status is ExecutionStatus.FAILED
    assert "cancelled but replacement failed" in report.reason


# --- Eccezione dall'exchange ---

def test_exchange_exception_returns_failed() -> None:
    mock_exchange = MagicMock()
    mock_exchange.place_market_order.side_effect = RuntimeError("Timeout API")

    proposal = TradeProposal(
        action=TradeAction.BUY,
        order_type=OrderType.MARKET,
        confidence=0.8,
        reason="segnale forte",
        details=TradeProposalDetails(quantity=0.001),
    )
    agent = ExecutionTraderAgent(exchange_client=mock_exchange)
    report = agent.run(_make_input(proposal, APPROVED))

    assert report.execution_status is ExecutionStatus.FAILED
    assert "Timeout API" in report.reason


# --- Guardrail: cap notional ---

def test_guardrail_notional_cap_blocks_order() -> None:
    """Un ordine il cui notional supera max_order_notional_usdc viene bloccato."""
    proposal = TradeProposal(
        action=TradeAction.BUY,
        order_type=OrderType.LIMIT,
        confidence=0.85,
        reason="segnale forte",
        details=TradeProposalDetails(quantity=0.01, price=50_000.0),
    )
    agent = ExecutionTraderAgent(exchange_client=MagicMock())
    report = agent.run(_make_input(proposal, APPROVED, max_order_notional_usdc=400.0))

    assert report.execution_status is ExecutionStatus.NOT_EXECUTED
    assert "Guardrail" in report.reason
    assert "notional" in report.reason


def test_guardrail_notional_within_cap_passes() -> None:
    """Un ordine entro il cap notional viene eseguito normalmente."""
    mock_exchange = MagicMock()
    mock_exchange.place_limit_order.return_value = {"orderId": "X"}
    proposal = TradeProposal(
        action=TradeAction.BUY,
        order_type=OrderType.LIMIT,
        confidence=0.85,
        reason="segnale",
        details=TradeProposalDetails(quantity=0.001, price=50_000.0),
    )
    agent = ExecutionTraderAgent(exchange_client=mock_exchange)
    report = agent.run(_make_input(proposal, APPROVED, max_order_notional_usdc=1000.0))

    assert report.execution_status is ExecutionStatus.EXECUTED


# --- Guardrail: cap percentuale portafoglio ---

def test_guardrail_portfolio_pct_cap_blocks_order() -> None:
    """Un ordine che supera max_position_pct del portafoglio viene bloccato."""
    portfolio = PortfolioState(
        usdc_balance=0.0,
        usdc_balance_total=0.0,
        usdc_value=1000.0,
        portfolio_qty_free=0.0,
        portfolio_qty_total=0.0,
    )
    mandate = InvestmentMandate(
        max_drawdown_pct=15.0,
        horizon="Intraday",
        max_position_pct=10.0,
    )
    proposal = TradeProposal(
        action=TradeAction.BUY,
        order_type=OrderType.LIMIT,
        confidence=0.8,
        reason="segnale",
        details=TradeProposalDetails(quantity=0.002, price=100_000.0),
    )
    agent = ExecutionTraderAgent(exchange_client=MagicMock())
    report = agent.run(
        _make_input(
            proposal, APPROVED,
            portfolio=portfolio,
            mandate=mandate,
            max_order_notional_usdc=1_000_000.0,
        )
    )

    assert report.execution_status is ExecutionStatus.NOT_EXECUTED
    assert "Guardrail" in report.reason
    assert "%" in report.reason


# --- Guardrail: order_id non trovato per CANCEL_AND_REPLACE ---

def test_guardrail_cancel_replace_unknown_order_id_blocks() -> None:
    """CANCEL_AND_REPLACE bloccato se order_id non è negli open_orders."""
    portfolio = PortfolioState(
        usdc_balance=500.0,
        usdc_balance_total=500.0,
        usdc_value=1000.0,
        portfolio_qty_free=0.0,
        portfolio_qty_total=0.0,
        open_orders=[{"orderId": "111", "clientOrderId": "abc"}],
    )
    proposal = TradeProposal(
        action=TradeAction.CANCEL_AND_REPLACE_ORDER,
        order_type=OrderType.LIMIT,
        confidence=0.7,
        reason="update prezzo",
        details=TradeProposalDetails(
            order_id="999", side=OrderSide.BUY, quantity=0.001, price=97000.0,
        ),
    )
    agent = ExecutionTraderAgent(exchange_client=MagicMock())
    report = agent.run(
        _make_input(proposal, APPROVED, portfolio=portfolio, max_order_notional_usdc=1_000_000.0)
    )

    assert report.execution_status is ExecutionStatus.NOT_EXECUTED
    assert "Guardrail" in report.reason
    assert "order_id" in report.reason


def test_guardrail_cancel_replace_known_order_id_passes() -> None:
    """CANCEL_AND_REPLACE procede se order_id è presente in open_orders."""
    mock_exchange = MagicMock()
    mock_exchange.cancel_order.return_value = {"status": "CANCELED"}
    mock_exchange.place_limit_order.return_value = {"orderId": "new_order"}

    portfolio = PortfolioState(
        usdc_balance=500.0,
        usdc_balance_total=500.0,
        usdc_value=1_000_000.0,
        portfolio_qty_free=0.0,
        portfolio_qty_total=0.0,
        open_orders=[{"orderId": "999", "clientOrderId": "abc"}],
    )
    proposal = TradeProposal(
        action=TradeAction.CANCEL_AND_REPLACE_ORDER,
        order_type=OrderType.LIMIT,
        confidence=0.7,
        reason="update prezzo",
        details=TradeProposalDetails(
            order_id="999", side=OrderSide.BUY, quantity=0.001, price=97000.0,
        ),
    )
    agent = ExecutionTraderAgent(exchange_client=mock_exchange)
    report = agent.run(
        _make_input(proposal, APPROVED, portfolio=portfolio, max_order_notional_usdc=1_000_000.0)
    )

    assert report.execution_status is ExecutionStatus.EXECUTED


# --- SELL_OCO ---

def test_sell_oco_calls_place_oco_sell() -> None:
    """SELL_OCO approvato deve chiamare place_oco_sell con i parametri corretti."""
    mock_exchange = MagicMock()
    mock_exchange.place_oco_sell.return_value = {
        "orderListId": 42,
        "orders": [{"orderId": "101"}, {"orderId": "102"}],
    }

    portfolio = PortfolioState(
        usdc_balance=0.0,
        usdc_balance_total=0.0,
        usdc_value=5000.0,
        portfolio_qty_free=0.01,
        portfolio_qty_total=0.01,
    )
    proposal = TradeProposal(
        action=TradeAction.SELL_OCO,
        order_type=OrderType.LIMIT,
        confidence=0.79,
        reason="OCO su posizione",
        details=TradeProposalDetails(
            quantity=0.005, price=115_000.0, sl_stop_price=92_000.0,
        ),
    )
    agent = ExecutionTraderAgent(exchange_client=mock_exchange)
    report = agent.run(
        _make_input(
            proposal, APPROVED,
            portfolio=portfolio,
            current_price=100_000.0,
            max_order_notional_usdc=1_000_000.0,
        )
    )

    assert report.execution_status is ExecutionStatus.EXECUTED
    mock_exchange.place_oco_sell.assert_called_once_with(
        "BTCUSDC", 0.005, 115_000.0, 92_000.0,
    )
    assert report.execution_details["orderListId"] == 42


def test_sell_oco_guardrail_inverted_prices_blocks() -> None:
    """SELL_OCO bloccato se tp_price <= current_price."""
    portfolio = PortfolioState(
        usdc_balance=0.0,
        usdc_balance_total=0.0,
        usdc_value=5000.0,
        portfolio_qty_free=0.01,
        portfolio_qty_total=0.01,
    )
    proposal = TradeProposal(
        action=TradeAction.SELL_OCO,
        order_type=OrderType.LIMIT,
        confidence=0.79,
        reason="OCO con TP sotto il prezzo corrente",
        details=TradeProposalDetails(
            quantity=0.005,
            price=90_000.0,   # TP sotto il current (100k) → invalido
            sl_stop_price=85_000.0,
        ),
    )
    agent = ExecutionTraderAgent(exchange_client=MagicMock())
    report = agent.run(
        _make_input(
            proposal, APPROVED,
            portfolio=portfolio,
            current_price=100_000.0,
            max_order_notional_usdc=1_000_000.0,
        )
    )

    assert report.execution_status is ExecutionStatus.NOT_EXECUTED
    assert "Guardrail SELL_OCO" in report.reason
    assert "ordinamento" in report.reason


def test_sell_oco_guardrail_qty_exceeds_free_blocks() -> None:
    """SELL_OCO bloccato se quantity supera portfolio_qty_free."""
    portfolio = PortfolioState(
        usdc_balance=0.0,
        usdc_balance_total=0.0,
        usdc_value=5000.0,
        portfolio_qty_free=0.002,  # libera meno di quanto si vuole vendere
        portfolio_qty_total=0.01,
    )
    proposal = TradeProposal(
        action=TradeAction.SELL_OCO,
        order_type=OrderType.LIMIT,
        confidence=0.79,
        reason="OCO con qty maggiore del disponibile",
        details=TradeProposalDetails(
            quantity=0.005,
            price=115_000.0,
            sl_stop_price=92_000.0,
        ),
    )
    agent = ExecutionTraderAgent(exchange_client=MagicMock())
    report = agent.run(
        _make_input(
            proposal, APPROVED,
            portfolio=portfolio,
            current_price=100_000.0,
            max_order_notional_usdc=1_000_000.0,
        )
    )

    assert report.execution_status is ExecutionStatus.NOT_EXECUTED
    assert "Guardrail SELL_OCO" in report.reason
    assert "portfolio_qty_free" in report.reason
