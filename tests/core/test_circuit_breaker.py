"""Test della classe CircuitBreaker e dell'helper build_error_signature."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pytest

from src.core.circuit_breaker import CircuitBreaker, build_error_signature
from src.core.exceptions import CycleExecutionError


def _make_breaker(
    threshold: int = 3,
    pause_log_interval_seconds: float = 3600.0,
    now: datetime | None = None,
) -> tuple[CircuitBreaker, list[datetime]]:
    """Costruisce un breaker con `now_fn` controllabile via lista mutevole.

    Restituisce ``(breaker, clock)``. Modificare ``clock[0]`` cambia l'ora che
    il breaker leggerà al prossimo accesso.
    """
    logger = logging.getLogger("test_circuit_breaker")
    start = now or datetime(2026, 5, 20, 12, 0, 0, tzinfo=timezone.utc)
    clock: list[datetime] = [start]
    breaker = CircuitBreaker(
        logger=logger,
        threshold=threshold,
        pause_log_interval_seconds=pause_log_interval_seconds,
        now_fn=lambda: clock[0],
    )
    return breaker, clock


def test_threshold_must_be_positive() -> None:
    logger = logging.getLogger("test")
    with pytest.raises(ValueError):
        CircuitBreaker(logger=logger, threshold=0)


def test_counter_increments_on_same_signature() -> None:
    breaker, _ = _make_breaker(threshold=3)

    assert breaker.record_error("sig-A") is False
    assert breaker.consecutive_count == 1
    assert breaker.record_error("sig-A") is False
    assert breaker.consecutive_count == 2
    assert breaker.is_tripped() is False


def test_counter_resets_on_different_signature() -> None:
    breaker, _ = _make_breaker(threshold=3)

    breaker.record_error("sig-A")
    breaker.record_error("sig-A")
    assert breaker.consecutive_count == 2

    breaker.record_error("sig-B")
    assert breaker.consecutive_count == 1
    assert breaker.last_signature == "sig-B"


def test_counter_resets_on_record_success() -> None:
    breaker, _ = _make_breaker(threshold=3)

    breaker.record_error("sig-A")
    breaker.record_error("sig-A")
    breaker.record_success()

    assert breaker.consecutive_count == 0
    assert breaker.last_signature is None


def test_record_error_returns_true_only_on_trip() -> None:
    breaker, _ = _make_breaker(threshold=3)

    assert breaker.record_error("sig-A") is False
    assert breaker.record_error("sig-A") is False
    assert breaker.record_error("sig-A") is True
    assert breaker.is_tripped() is True
    assert breaker.record_error("sig-A") is False


def test_record_success_is_noop_once_tripped() -> None:
    breaker, _ = _make_breaker(threshold=2)

    breaker.record_error("sig-A")
    breaker.record_error("sig-A")
    assert breaker.is_tripped() is True

    breaker.record_success()

    assert breaker.is_tripped() is True
    assert breaker.consecutive_count == 2


def test_maybe_log_paused_status_logs_first_time_immediately(
    caplog: pytest.LogCaptureFixture,
) -> None:
    breaker, _ = _make_breaker(threshold=2, pause_log_interval_seconds=3600)
    breaker.record_error("sig-A")
    breaker.record_error("sig-A")

    with caplog.at_level(logging.WARNING, logger="test_circuit_breaker"):
        breaker.maybe_log_paused_status()

    assert any("Circuit breaker attivo" in r.message for r in caplog.records)


def test_maybe_log_paused_status_respects_interval(
    caplog: pytest.LogCaptureFixture,
) -> None:
    breaker, clock = _make_breaker(threshold=2, pause_log_interval_seconds=3600)
    breaker.record_error("sig-A")
    breaker.record_error("sig-A")

    with caplog.at_level(logging.WARNING, logger="test_circuit_breaker"):
        breaker.maybe_log_paused_status()
        clock[0] = clock[0] + timedelta(seconds=60)
        breaker.maybe_log_paused_status()

    assert sum("Circuit breaker attivo" in r.message for r in caplog.records) == 1

    caplog.clear()
    clock[0] = clock[0] + timedelta(seconds=3600)
    with caplog.at_level(logging.WARNING, logger="test_circuit_breaker"):
        breaker.maybe_log_paused_status()

    assert sum("Circuit breaker attivo" in r.message for r in caplog.records) == 1


def test_maybe_log_paused_status_noop_when_not_tripped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    breaker, _ = _make_breaker(threshold=3)
    breaker.record_error("sig-A")

    with caplog.at_level(logging.WARNING, logger="test_circuit_breaker"):
        breaker.maybe_log_paused_status()

    assert not caplog.records


def test_build_error_signature_basic() -> None:
    exc = ValueError("oops")
    assert build_error_signature(exc) == "ValueError:oops"


def test_build_error_signature_unwraps_cycle_execution_error() -> None:
    original = RuntimeError("boom inside")
    wrapper = CycleExecutionError("wrap", original=original)

    assert build_error_signature(wrapper) == "RuntimeError:boom inside"
