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


def atr(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
) -> float | None:
    """Average True Range (Wilder's smoothing).

    True Range = max(high - low, |high - prev_close|, |low - prev_close|).
    L'ATR e' una media esponenziale del TR con alpha = 1/period (smoothing
    classico di Wilder). Restituisce ``None`` se le tre serie non hanno la
    stessa lunghezza o se i dati sono insufficienti.
    """
    if not (len(highs) == len(lows) == len(closes)):
        return None
    if len(closes) < period + 1:
        return None

    h = pd.Series(highs)
    low = pd.Series(lows)
    c = pd.Series(closes)
    prev_c = c.shift(1)
    tr = pd.concat(
        [(h - low).abs(), (h - prev_c).abs(), (low - prev_c).abs()],
        axis=1,
    ).max(axis=1)
    tr = tr.iloc[1:]
    result = tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean().iloc[-1]
    if pd.isna(result):
        return None
    return float(result)


def compute_indicators_bundle(
    closes: list[float],
    *,
    highs: list[float] | None = None,
    lows: list[float] | None = None,
) -> dict[str, float | None]:
    """Calcola un bundle di indicatori tecnici e i valori precedenti.

    Calcola RSI(14), EMA(21), SMA(50), MACD e (se forniti `highs` e `lows`)
    ATR(14), sia sulla serie intera (`closes`) sia sulla serie precedente
    (`closes[:-1]`). Il dict ritornato contiene sempre le 14 chiavi attese
    da `MarketDataSnapshot.indicators`; i valori sono `None` quando i dati
    sono insufficienti per l'indicatore o quando `highs`/`lows` non sono
    disponibili (ATR).

    Quando `closes` ha 0 o 1 elementi la serie precedente coincide con
    `closes` (fallback): in pratica i due valori "current" e "prev" diventano
    identici (entrambi `None` o entrambi calcolati sulla stessa serie).
    """
    closes_prev = closes[:-1] if len(closes) > 1 else closes

    rsi_val = rsi(closes, period=14)
    rsi_prev = rsi(closes_prev, period=14)

    ema_val = ema(closes, period=21)
    ema_prev = ema(closes_prev, period=21)

    sma_val = sma(closes, period=50)
    sma_prev = sma(closes_prev, period=50)

    macd_val = macd(closes)
    macd_prev = macd(closes_prev)

    if highs is not None and lows is not None:
        atr_val = atr(highs, lows, closes, period=14)
        if len(closes) > 1:
            atr_prev = atr(highs[:-1], lows[:-1], closes_prev, period=14)
        else:
            atr_prev = atr_val
    else:
        atr_val = None
        atr_prev = None

    return {
        "rsi": rsi_val,
        "rsi_prev": rsi_prev,
        "ema_21": ema_val,
        "ema_21_prev": ema_prev,
        "sma_50": sma_val,
        "sma_50_prev": sma_prev,
        "macd": macd_val[0] if macd_val else None,
        "macd_prev": macd_prev[0] if macd_prev else None,
        "macd_signal": macd_val[1] if macd_val else None,
        "macd_signal_prev": macd_prev[1] if macd_prev else None,
        "macd_hist": macd_val[2] if macd_val else None,
        "macd_hist_prev": macd_prev[2] if macd_prev else None,
        "atr": atr_val,
        "atr_prev": atr_prev,
    }
