"""Test per ExecutionTraderAgent.run() con mock dell'exchange client."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.agents.execution_trader import ExecutionTraderAgent
from src.core.contracts import (
    ExecutionInput,
    ExecutionStatus,
    OrderSide,
    OrderType,
    RiskAssessment,
    RiskDecision,
    TradeAction,
    TradeProposal,
    TradeProposalDetails,
)

def _make_input(
    proposal: TradeProposal,
    risk: RiskAssessment,
) -> ExecutionInput:
    return ExecutionInput(
        symbol="BTCUSDC",
        proposal=proposal,
        risk_assessment=risk,
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
    agent = ExecutionTraderAgent(exchange_client=mock_exchange)
    report = agent.run(_make_input(proposal, APPROVED))

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

    assert report.execution_status is ExecutionStatus.FAILED
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
    agent = ExecutionTraderAgent(exchange_client=mock_exchange)
    report = agent.run(_make_input(proposal, APPROVED))

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
