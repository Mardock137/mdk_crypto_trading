from __future__ import annotations

from src.utils.indicators import compute_indicators_bundle, ema, macd, rsi, sma


_EXPECTED_BUNDLE_KEYS = {
    "rsi", "rsi_prev",
    "ema_21", "ema_21_prev",
    "sma_50", "sma_50_prev",
    "macd", "macd_prev",
    "macd_signal", "macd_signal_prev",
    "macd_hist", "macd_hist_prev",
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


# ---- compute_indicators_bundle ----


def test_bundle_returns_all_12_keys_on_sufficient_data() -> None:
    """Con una serie abbastanza lunga, il dict ritornato ha tutte le 12 chiavi attese
    e i valori non sono None."""
    closes = [100.0 + i * 0.5 for i in range(60)]
    bundle = compute_indicators_bundle(closes)

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


def test_bundle_returns_all_12_keys_with_none_on_short_input() -> None:
    """Con una serie troppo corta, il dict ritornato ha comunque tutte le 12 chiavi,
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
