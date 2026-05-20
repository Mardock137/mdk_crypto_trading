"""Circuit breaker per fermare il bot dopo N errori consecutivi identici.

Quando lo stesso errore (stesso tipo + stesso messaggio) si ripete `threshold`
volte di seguito, il breaker scatta ("trip"): il `TradingRunner` smette di
eseguire cicli ma il processo resta vivo (heartbeat aggiornato, container in
piedi, Telegram raggiungibile). Il ripristino e' manuale: l'operatore deve
riavviare il container (`docker compose restart trading-bot`).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone


class CircuitBreaker:
    """Conta errori consecutivi identici e si trippa al raggiungimento della soglia.

    Una volta trippato resta tale finche' non viene resettato dall'esterno
    (es. riavvio del processo). Non resetta da solo: e' una scelta voluta per
    forzare l'intervento umano dopo problemi sistematici.
    """

    DEFAULT_THRESHOLD = 3
    PAUSE_LOG_INTERVAL_SECONDS = 3600.0

    def __init__(
        self,
        logger: logging.Logger,
        threshold: int = DEFAULT_THRESHOLD,
        pause_log_interval_seconds: float = PAUSE_LOG_INTERVAL_SECONDS,
        now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if threshold < 1:
            raise ValueError("threshold deve essere >= 1")
        self._logger = logger
        self._threshold = threshold
        self._pause_log_interval_seconds = pause_log_interval_seconds
        self._now_fn = now_fn
        self._last_signature: str | None = None
        self._consecutive_count = 0
        self._tripped = False
        self._tripped_at: datetime | None = None
        self._last_pause_log_at: datetime | None = None

    @property
    def threshold(self) -> int:
        return self._threshold

    @property
    def consecutive_count(self) -> int:
        return self._consecutive_count

    @property
    def last_signature(self) -> str | None:
        return self._last_signature

    def is_tripped(self) -> bool:
        return self._tripped

    def record_error(self, signature: str) -> bool:
        """Registra un errore. Ritorna True SOLO nell'istante in cui scatta.

        Se gia' trippato, e' un no-op e ritorna False (non vogliamo inviare
        notifiche duplicate).
        """
        if self._tripped:
            return False

        if signature == self._last_signature:
            self._consecutive_count += 1
        else:
            self._last_signature = signature
            self._consecutive_count = 1

        if self._consecutive_count >= self._threshold:
            self._tripped = True
            self._tripped_at = self._now_fn()
            return True
        return False

    def record_success(self) -> None:
        """Resetta il contatore. No-op se gia' trippato."""
        if self._tripped:
            return
        self._last_signature = None
        self._consecutive_count = 0

    def maybe_log_paused_status(self) -> None:
        """Se trippato, logga un reminder ad intervalli regolari.

        Pensato per essere chiamato ad ogni ciclo del main loop quando il
        breaker e' scattato. Logga la prima volta subito e poi ogni
        ``pause_log_interval_seconds``.
        """
        if not self._tripped:
            return
        now = self._now_fn()
        if (
            self._last_pause_log_at is None
            or (now - self._last_pause_log_at).total_seconds()
            >= self._pause_log_interval_seconds
        ):
            self._logger.warning(
                "Circuit breaker attivo: cicli sospesi dopo %d errori identici "
                "consecutivi (ultimo: %s). Riavvio manuale richiesto.",
                self._consecutive_count,
                self._last_signature,
            )
            self._last_pause_log_at = now


def build_error_signature(exc: BaseException) -> str:
    """Costruisce una signature stabile per confrontare errori consecutivi.

    Per ``CycleExecutionError`` usa l'eccezione originale (``exc.original``):
    il wrapper porta solo metadati di contesto, l'identita' dell'errore e'
    nell'eccezione sottostante.
    """
    from src.core.exceptions import CycleExecutionError

    target: BaseException = exc
    if isinstance(exc, CycleExecutionError):
        target = exc.original
    return f"{type(target).__name__}:{target}"
