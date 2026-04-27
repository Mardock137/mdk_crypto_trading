from __future__ import annotations

import pandas as pd


def sma(closes: list[float], period: int) -> float | None:
    """Simple Moving Average. Restituisce None se i dati sono insufficienti."""
    if len(closes) < period:
        return None
    series = pd.Series(closes)
    result = series.rolling(window=period).mean().iloc[-1]
    return float(result)


def ema(closes: list[float], period: int) -> float | None:
    """Exponential Moving Average. Restituisce None se i dati sono insufficienti."""
    if len(closes) < period:
        return None
    series = pd.Series(closes)
    result = series.ewm(span=period, adjust=False).mean().iloc[-1]
    return float(result)


def rsi(closes: list[float], period: int = 14) -> float | None:
    """Relative Strength Index. Restituisce None se i dati sono insufficienti."""
    if len(closes) < period + 1:
        return None
    series = pd.Series(closes)
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean().iloc[-1]
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - (100.0 / (1.0 + rs)))


def macd(
    closes: list[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> tuple[float, float, float] | None:
    """MACD (macd_line, signal_line, histogram). Restituisce None se dati insufficienti."""
    min_required = slow + signal_period
    if len(closes) < min_required:
        return None
    series = pd.Series(closes)
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line
    return (
        float(macd_line.iloc[-1]),
        float(signal_line.iloc[-1]),
        float(histogram.iloc[-1]),
    )
