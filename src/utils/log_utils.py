from __future__ import annotations

from typing import Any


def truncate_for_log(value: Any, max_len: int = 200) -> str:
    """Converte ``value`` in stringa e la tronca a ``max_len`` caratteri.

    Usato per evitare che blob di risposta LLM (potenzialmente molto lunghi)
    finiscano per intero nei messaggi di WARNING su file e console Docker.
    Il contenuto integrale è già disponibile a livello DEBUG.
    """
    text = repr(value) if not isinstance(value, str) else value
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"…[+{len(text) - max_len}]"
