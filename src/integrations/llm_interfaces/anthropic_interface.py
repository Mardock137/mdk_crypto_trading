from __future__ import annotations

import json
import logging
from typing import Any, Mapping

from anthropic import (
    Anthropic,
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.integrations.llm_interfaces.base_llm_interface import BaseLlmInterface

_logger = logging.getLogger("mdk_crypto_trading.anthropic_interface")

# Eccezioni temporanee su cui fare retry automatico
_RETRYABLE_ERRORS = (
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
)


class AnthropicInterface(BaseLlmInterface):
    """Implementazione di BaseLlmInterface per il provider Anthropic (Claude).

    Supporta sia i modelli "classici" (es. Sonnet 4.6) sia quelli che richiedono
    adaptive thinking (es. Opus 4.7). La distinzione avviene tramite il parametro
    ``thinking_effort``:

    - ``None`` (default): comportamento classico — viene passata ``temperature``
      e la risposta viene letta dal primo blocco ``text``.
    - stringa (es. ``"high"``): abilita il thinking adattivo passando
      ``thinking={"type": "adaptive"}`` e ``output_config={"effort": ...}``,
      NON passa ``temperature`` (non accettata dai modelli con thinking) e la
      risposta viene estratta concatenando solo i blocchi ``text`` (scartando
      quelli ``thinking``).
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        thinking_effort: str | None = None,
    ) -> None:
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens or 1024
        self._thinking_effort = thinking_effort
        self._client = Anthropic(api_key=api_key)

    @property
    def model_name(self) -> str:
        return self._model

    def _build_kwargs(self) -> dict[str, Any]:
        """Costruisce i kwargs dinamici per messages.create().

        Con thinking_effort: include thinking (adaptive) e output_config (effort),
        esclude temperature.
        Senza thinking_effort: include temperature, esclude thinking e output_config.
        """
        kwargs: dict[str, Any] = {}
        if self._thinking_effort is not None:
            kwargs["thinking"] = {"type": "adaptive"}
            kwargs["output_config"] = {"effort": self._thinking_effort}
        else:
            kwargs["temperature"] = self._temperature
        return kwargs

    @retry(
        retry=retry_if_exception_type(_RETRYABLE_ERRORS),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def generate_json(
        self,
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": json.dumps(dict(user_payload))}
                ],
                **self._build_kwargs(),
            )
            raw = _extract_text(response)
            if not raw or not raw.strip():
                _logger.warning(
                    "Anthropic risposta vuota | stop_reason: %s | usage: %s",
                    response.stop_reason,
                    response.usage,
                )
                raise RuntimeError("Risposta vuota dal provider Anthropic.")
            result: dict[str, Any] = json.loads(_strip_markdown_json(raw))
            if not result:
                raise RuntimeError("Il provider Anthropic ha risposto con un JSON vuoto.")
            return result
        except _RETRYABLE_ERRORS:
            raise
        except APIStatusError as exc:
            raise RuntimeError(f"Errore API Anthropic: {exc}") from exc
        except json.JSONDecodeError as exc:
            _logger.warning("Risposta raw non decodificabile di Anthropic: %r", raw)
            raise RuntimeError(
                f"Impossibile decodificare la risposta JSON di Anthropic: {exc}"
            ) from exc


def _extract_text(response: Any) -> str:
    """Estrae il testo dalla risposta Anthropic, ignorando i blocchi thinking.

    La risposta Anthropic e una lista di content blocks. I modelli con thinking
    (es. Opus 4.7) possono includere blocchi ``thinking`` insieme a quelli
    ``text``: questi vanno scartati a prescindere dal loro contenuto (su Opus
    4.7 di default arrivano vuoti, ma con ``display: "summarized"`` possono
    contenere un riassunto del ragionamento). I modelli classici restituiscono
    solo blocchi ``text``. Consideriamo "text" qualsiasi blocco che non sia
    esplicitamente ``thinking``, per retrocompatibilita.
    """
    if not response.content:
        return ""
    parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "thinking":
            continue
        text = getattr(block, "text", "") or ""
        if isinstance(text, str) and text:
            parts.append(text)
    return "".join(parts)


def _strip_markdown_json(text: str) -> str:
    """Rimuove il wrapping markdown da una risposta JSON di Claude.

    Claude a volte restituisce il JSON wrappato in un code block markdown
    (```json ... ```) nonostante il prompt chieda JSON puro. Questa funzione
    estrae il contenuto grezzo del JSON in tre passi:
    1. Rimuove il code block markdown se presente (```json o ```).
    2. Come fallback, estrae il sottostringa dal primo '{' all'ultimo '}'.
    3. Se la stringa e gia JSON puro, la restituisce invariata.
    """
    stripped = text.strip()

    # Caso 1: code block markdown (```json ... ``` oppure ``` ... ```)
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        if first_newline != -1:
            inner = stripped[first_newline + 1:]
            if inner.rstrip().endswith("```"):
                inner = inner.rstrip()[:-3].rstrip()
            return inner.strip()

    # Caso 2: testo extra prima o dopo il JSON — estrae dal primo '{' all'ultimo '}'
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return stripped[start : end + 1]

    # Caso 3: stringa invariata (gia JSON puro o vuota — gestita a monte)
    return stripped
