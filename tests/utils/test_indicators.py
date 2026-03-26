from __future__ import annotations

from src.utils.indicators import ema, macd, rsi, sma


# ---- Dati insufficienti → None ----


def test_sma_returns_none_if_insufficient_data() -> None:
    assert sma([1.0, 2.0], period=5) is None


def test_ema_returns_none_if_insufficient_data() -> None:
    assert ema([1.0, 2.0], period=5) is None


def test_rsi_returns_none_if_insufficient_data() -> None:
    assert rsi([1.0, 2.0, 3.0], period=14) is None


def test_macd_returns_none_if_insufficient_data() -> None:
    assert macd([1.0] * 30) is None


# ---- Calcolo corretto con dati noti ----


def test_sma_with_known_values() -> None:
    # SMA(5) di [1, 2, 3, 4, 5] = media(1,2,3,4,5) = 3.0
    result = sma([1.0, 2.0, 3.0, 4.0, 5.0], period=5)
    assert result is not None
    assert abs(result - 3.0) < 1e-6


def test_ema_with_known_values() -> None:
    closes = [10.0] * 20 + [20.0]
    result = ema(closes, period=10)
    assert result is not None
    # L'EMA si muove verso 20 ma non ci arriva in una sola candela
    assert 10.0 < result < 20.0


def test_rsi_with_all_gains() -> None:
    # Serie monotonamente crescente → RSI vicino a 100
    closes = [float(i) for i in range(1, 25)]
    result = rsi(closes, period=14)
    assert result is not None
    assert result > 90.0


def test_rsi_with_all_losses() -> None:
    # Serie monotonamente decrescente → RSI vicino a 0
    closes = [float(i) for i in range(25, 1, -1)]
    result = rsi(closes, period=14)
    assert result is not None
    assert result < 10.0


def test_macd_returns_three_floats() -> None:
    # Serie sufficiente per calcolare MACD (almeno 35 valori)
    closes = [100.0 + i * 0.5 for i in range(50)]
    result = macd(closes)
    assert result is not None
    macd_line, signal_line, histogram = result
    assert isinstance(macd_line, float)
    assert isinstance(signal_line, float)
    assert isinstance(histogram, float)
    # Con serie crescente, MACD dovrebbe essere positivo
    assert macd_line > 0
