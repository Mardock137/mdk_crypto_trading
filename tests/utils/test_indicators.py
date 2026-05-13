from __future__ import annotations

from src.utils.indicators import atr, compute_indicators_bundle, ema, macd, rsi, sma


_EXPECTED_BUNDLE_KEYS = {
    "rsi", "rsi_prev",
    "ema_21", "ema_21_prev",
    "sma_50", "sma_50_prev",
    "macd", "macd_prev",
    "macd_signal", "macd_signal_prev",
    "macd_hist", "macd_hist_prev",
    "atr", "atr_prev",
}


# ---- Dati insufficienti → None ----


def test_sma_returns_none_if_insufficient_data() -> None:
    assert sma([1.0, 2.0], period=5) is None


def test_ema_returns_none_if_insufficient_data() -> None:
    assert ema([1.0, 2.0], period=5) is None


def test_rsi_returns_none_if_insufficient_data() -> None:
    assert rsi([1.0, 2.0, 3.0], period=14) is None


def test_macd_returns_none_if_insufficient_data() -> None:
    assert macd([1.0] * 30) is None


def test_atr_returns_none_if_insufficient_data() -> None:
    assert atr([1.0] * 5, [0.5] * 5, [0.8] * 5, period=14) is None


def test_atr_returns_none_if_series_lengths_mismatch() -> None:
    """Se highs/lows/closes hanno lunghezze diverse, atr() deve ritornare None."""
    assert atr([1.0] * 20, [0.5] * 19, [0.8] * 20, period=14) is None


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


def test_atr_with_constant_range_returns_that_range() -> None:
    """Con range costante (high-low fisso e closes invariati), ATR converge al range."""
    # 30 candele tutte con high=110, low=100, close=105 → TR = 10 per ogni periodo
    highs = [110.0] * 30
    lows = [100.0] * 30
    closes = [105.0] * 30
    result = atr(highs, lows, closes, period=14)
    assert result is not None
    assert abs(result - 10.0) < 1e-6


def test_atr_increases_when_volatility_grows() -> None:
    """Una serie a volatilita' crescente deve produrre un ATR > di una serie tranquilla."""
    # Serie 1: range piccolo
    calm_h = [101.0] * 30
    calm_l = [100.0] * 30
    calm_c = [100.5] * 30
    # Serie 2: range piu grande
    wild_h = [110.0] * 30
    wild_l = [100.0] * 30
    wild_c = [105.0] * 30

    calm = atr(calm_h, calm_l, calm_c, period=14)
    wild = atr(wild_h, wild_l, wild_c, period=14)
    assert calm is not None and wild is not None
    assert wild > calm


# ---- compute_indicators_bundle ----


def test_bundle_returns_all_keys_on_sufficient_data_without_ohlc() -> None:
    """Senza highs/lows il bundle ha tutte le chiavi attese: atr e atr_prev sono None,
    gli altri indicatori popolati."""
    closes = [100.0 + i * 0.5 for i in range(60)]
    bundle = compute_indicators_bundle(closes)

    assert set(bundle.keys()) == _EXPECTED_BUNDLE_KEYS
    assert bundle["atr"] is None
    assert bundle["atr_prev"] is None
    for key, value in bundle.items():
        if key in {"atr", "atr_prev"}:
            continue
        assert value is not None, f"Atteso valore non-None per {key!r}"


def test_bundle_returns_all_keys_with_ohlc_includes_atr() -> None:
    """Con highs/lows forniti il bundle popola anche atr e atr_prev."""
    closes = [100.0 + i * 0.5 for i in range(60)]
    highs = [c + 1.0 for c in closes]
    lows = [c - 1.0 for c in closes]
    bundle = compute_indicators_bundle(closes, highs=highs, lows=lows)

    assert set(bundle.keys()) == _EXPECTED_BUNDLE_KEYS
    for key, value in bundle.items():
        assert value is not None, f"Atteso valore non-None per {key!r}"


def test_bundle_prev_values_match_calc_on_closes_minus_last() -> None:
    """I valori `*_prev` devono coincidere con il calcolo degli indicatori
    sulla serie `closes[:-1]`."""
    closes = [100.0 + i * 0.5 for i in range(60)]
    bundle = compute_indicators_bundle(closes)
    closes_prev = closes[:-1]

    assert bundle["rsi_prev"] == rsi(closes_prev, period=14)
    assert bundle["ema_21_prev"] == ema(closes_prev, period=21)
    assert bundle["sma_50_prev"] == sma(closes_prev, period=50)

    macd_prev = macd(closes_prev)
    assert macd_prev is not None
    assert bundle["macd_prev"] == macd_prev[0]
    assert bundle["macd_signal_prev"] == macd_prev[1]
    assert bundle["macd_hist_prev"] == macd_prev[2]


def test_bundle_returns_all_keys_with_none_on_short_input() -> None:
    """Con una serie troppo corta, il dict ritornato ha comunque tutte le chiavi attese,
    con valori `None` per gli indicatori che richiedono più dati."""
    bundle = compute_indicators_bundle([1.0, 2.0, 3.0])

    assert set(bundle.keys()) == _EXPECTED_BUNDLE_KEYS
    for value in bundle.values():
        assert value is None


def test_bundle_with_empty_list_returns_all_none() -> None:
    bundle = compute_indicators_bundle([])

    assert set(bundle.keys()) == _EXPECTED_BUNDLE_KEYS
    for value in bundle.values():
        assert value is None
