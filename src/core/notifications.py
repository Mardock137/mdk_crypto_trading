from __future__ import annotations

from src.core.contracts import OrderType, TradingCycleResult


def build_startup_message(symbol: str, mode: str, interval_seconds: int) -> str:
    """Messaggio Telegram di avvio bot."""
    return (
        f"<b>🚀 Bot STARTED</b>\n\n"
        f"Symbol: {symbol}\n"
        f"Mode: {mode}\n"
        f"Interval: {interval_seconds}s"
    )


def build_stop_message(symbol: str) -> str:
    """Messaggio Telegram di stop bot."""
    return f"<b>🛑 Bot STOPPED</b>\n\nSymbol: {symbol}"


def build_error_message(symbol: str, correlation_id: str, exc_class: str) -> str:
    """Messaggio Telegram di errore ciclo.

    Non include ``str(exc)`` per evitare leak di dati sensibili nei log
    Telegram. Il dettaglio completo è recuperabile via ``correlation_id``
    nei log locali.
    """
    return (
        f"<b>⚠️ Cycle ERROR</b>\n\n"
        f"Symbol: {symbol}\n"
        f"Error ID: {correlation_id}\n"
        f"Type: {exc_class}"
    )


def build_order_notification(
    symbol: str,
    mode: str,
    result: TradingCycleResult,
) -> str:
    """Costruisce il testo della notifica per un ordine eseguito.

    Per i MARKET order calcola il prezzo medio dai campi Binance
    ``cummulativeQuoteQty`` ed ``executedQty``.
    """
    report = result.execution_report
    proposal = result.trade_proposal
    details = proposal.details

    lines: list[str] = [
        "<b>✅ Order EXECUTED</b>",
        "",
        f"Action: {report.executed_action.value}",
        f"Type: {report.order_type.value}",
    ]

    if details.quantity is not None:
        lines.append(f"Quantity: {details.quantity}")

    if report.order_type is OrderType.MARKET:
        exec_d = report.execution_details
        cum_quote = exec_d.get("cummulativeQuoteQty")
        exec_qty = exec_d.get("executedQty")
        if cum_quote and exec_qty:
            try:
                avg_price = float(cum_quote) / float(exec_qty)
                lines.append(f"Price: {avg_price:.2f}")
                lines.append(f"Value: {float(cum_quote):.2f} USDC")
            except (ValueError, ZeroDivisionError):
                pass
    elif report.order_type is OrderType.LIMIT:
        if details.price is not None:
            lines.append(f"Price: {details.price:.2f}")
        notional = details.estimated_notional()
        if notional is not None:
            lines.append(f"Est. Value: {notional:.2f} USDC")

    lines.append(f"DM Confidence: {proposal.confidence:.2f}")
    lines.append(f"Symbol: {symbol}")
    lines.append(f"Mode: {mode}")

    return "\n".join(lines)
