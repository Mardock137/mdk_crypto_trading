# Configurazione

Il sistema usa due fonti di configurazione separate: il file `.env` per i segreti e la cartella `config/` per le configurazioni applicative.

---

## 📋 Indice

- [`.env` — Segreti e variabili d'ambiente](#env--segreti-e-variabili-dambiente)
- [`config/` — Configurazioni applicative](#config--configurazioni-applicative)
- [Distinzione tra `config/` e `.env`](#distinzione-tra-config-e-env)
- [🧪 Testing](#-testing)
- [🔍 Troubleshooting](#-troubleshooting)
- [📚 Riferimenti](#-riferimenti)

---

## `.env` — Segreti e variabili d'ambiente

Contiene chiavi API, modalità di esecuzione e variabili riservate. Mai committato su git.

| Variabile                 | Obbligatoria | Default  | Descrizione                                       |
|---------------------------|--------------|----------|---------------------------------------------------|
| `TRADING_MODE`            | sì           | —        | `DEMO` o `REAL`                                   |
| `KILL_SWITCH`             | no           | `1`      | Se `1`, forza tutte le operazioni a HOLD          |
| `CYCLE_INTERVAL_SECONDS`  | sì           | —        | Secondi tra un ciclo e l'altro                    |
| `LOG_LEVEL`               | no           | `INFO`   | `DEBUG`, `INFO`, `WARNING`, `ERROR`               |
| `CLAUDE_API_KEY`          | sì           | —        | Chiave API Anthropic (Claude)                     |
| `OPENAI_API_KEY`          | sì           | —        | Chiave API OpenAI                                 |
| `GEMINI_API_KEY`          | sì           | —        | Chiave API Google Gemini                          |
| `BINANCE_API_KEY`         | in REAL      | —        | Chiave API Binance produzione                     |
| `BINANCE_SECRET_KEY`      | in REAL      | —        | Secret Binance produzione                         |
| `BINANCE_DEMO_API_KEY`    | in DEMO      | —        | Chiave API Binance Demo Trading                   |
| `BINANCE_DEMO_SECRET_KEY` | in DEMO      | —        | Secret Binance Demo Trading                       |
| `BINANCE_DEMO_BASE_URL`   | in DEMO      | —        | URL Binance Demo (`https://demo-api.binance.com`) |
| `TELEGRAM_BOT_TOKEN`      | no           | —        | Token del bot Telegram (notifiche opzionali)      |
| `TELEGRAM_CHAT_ID`        | no           | —        | ID della chat Telegram di destinazione            |

Vedi `.env.example` per un template completo.

---

## `config/` — Configurazioni applicative

### `config/trading.yaml`

Regole operative statiche del sistema e mandato di investimento.

```yaml
min_order_usdc: 10.0
max_order_notional_usdc: 500.0
breakeven_trigger_pct: 2.0
oco_review_interval_hours: 24.0

mandate:
  max_drawdown_pct: 15.0
  horizon: "Intraday to swing (ore → giorni)"
  max_position_pct: 70.0
```

Campi:

- `min_order_usdc`: soglia minima del notional (quantità × prezzo) consentita per un singolo ordine, in USDC. Il guardrail nell'`ExecutionTraderAgent` blocca qualsiasi ordine il cui notional sia inferiore a questo valore, restituendo `NOT_EXECUTED` con reason tracciata negli event log — a specchio del guardrail massimo (`max_order_notional_usdc`). Difesa in profondità: affianca (non sostituisce) il filtro `minNotional` di Binance.
- `max_order_notional_usdc`: valore massimo del notional (quantità × prezzo) consentito per un singolo ordine, in USDC. Il guardrail nell'`ExecutionTraderAgent` blocca qualsiasi ordine il cui notional superi questo limite, restituendo `NOT_EXECUTED` con reason tracciata negli event log. Il fallback software (se il campo manca dal file) è `500.0`.
- `breakeven_trigger_pct`: soglia di profitto non realizzato (in percentuale) oltre la quale il runner sposta automaticamente lo Stop Loss dell'OCO attivo al prezzo di ingresso (breakeven). Il meccanismo è deterministico, viene eseguito prima della catena LLM e non coinvolge il Decision Maker. Non viene eseguito se il kill switch è attivo (`KILL_SWITCH=1`). Il fallback software è `2.0`.
- `oco_review_interval_hours`: ore trascorse dall'apertura di un OCO oltre le quali il runner imposta `oco_review_required = True` nel ciclo corrente. Quando il flag è `True`, il prompt del Decision Maker rende obbligatoria la valutazione esplicita dei livelli TP/SL. Il fallback software è `24.0`.
- `mandate.max_drawdown_pct`: drawdown massimo tollerato in percentuale.
- `mandate.horizon`: orizzonte temporale tipico delle operazioni (es. intraday, swing).
- `mandate.max_position_pct`: percentuale massima del capitale allocabile sulla singola posizione. Il guardrail nell'`ExecutionTraderAgent` calcola la percentuale rispetto al **valore totale del portafoglio** (USDC totali, liberi + bloccati in ordini aperti, più il controvalore totale delle monete). Il campo esiste già in vista del multi-simbolo.

Il mandate viene caricato all'avvio del runner tramite `load_mandate(trading_config)` in `src/utils/config.py` e propagato a ogni ciclo dentro `TradingCycleInput`. Se la sezione `mandate` manca o ha campi incompleti, il runner fallisce in fase di boot con un `ValueError` esplicito.

### `config/cycle_skip.yaml`

Configurazione del **pre-check deterministico** che decide se saltare un ciclo operativo quando il contesto di mercato e' rimasto sostanzialmente identico rispetto al precedente. Obiettivo: evitare di chiamare Analyst + Decision Maker (Opus con thinking) + Risk Manager quando non ci sono variazioni significative, risparmiando token e latenza.

```yaml
enabled: true
max_consecutive_skips: 4
thresholds:
  price_delta_pct: 0.5
  rsi_delta: 2.0
  macd_sign_must_match: true
  require_no_order_events: true
  require_previous_action_hold: true
```

Campi:

- `enabled`: se `false`, il pre-check e' disattivato e ogni ciclo esegue l'intera catena di agenti (comportamento pre-feature).
- `max_consecutive_skips`: dopo N skip consecutivi, il ciclo successivo viene sempre eseguito per intero (anche se il contesto e' invariato). Evita di restare "bloccati" in skip infinito.
- `thresholds.price_delta_pct`: variazione percentuale massima del prezzo tra ciclo precedente e corrente (oltre → no skip).
- `thresholds.rsi_delta`: variazione assoluta massima dell'RSI (oltre → no skip).
- `thresholds.macd_sign_must_match`: se `true`, il segno di `macd - macd_signal` deve essere uguale al ciclo precedente; un flip impedisce lo skip.
- `thresholds.require_no_order_events`: se `true`, qualsiasi cambiamento nel set di ordini aperti (nuovo ordine, fill, cancellazione) impedisce lo skip.
- `thresholds.require_previous_action_hold`: se `true`, lo skip e' consentito solo se l'azione del ciclo precedente era `HOLD`.

Se il file manca, il sistema applica fallback safe con `enabled=false` (nessun ciclo viene saltato). Lo snapshot del contesto precedente vive solo in memoria del runner: dopo ogni restart il primo ciclo e' sempre full.

### `config/symbols.yaml`

Simbolo di trading attivo e quote currency.

```yaml
symbol: BTCUSDC
quote_currency: USDC
```

- `symbol`: coppia di trading attiva (es. `BTCUSDC`, `ETHUSDC`)
- `quote_currency`: valuta di riferimento usata per calcolare saldi e controvalore. Deve corrispondere al suffisso del simbolo

### `config/llm_models/`

Configurazione dei modelli LLM usati dagli agenti. Un file YAML per agente.

**`market_analyst.yaml`** (provider: OpenAI):

```yaml
provider: openai
model: gpt-5.4
temperature: 0.2
max_tokens: 4096
```

**`decision_maker.yaml`** (provider: Anthropic, con adaptive thinking):

```yaml
provider: anthropic
model: claude-opus-4-7
thinking_effort: medium
max_tokens: 16384
```

**`risk_manager.yaml`** (provider: Gemini):

```yaml
provider: gemini
model: gemini-3.1-pro-preview
max_tokens: 4096
```

**`performance_reviewer.yaml`** (provider: Anthropic):

```yaml
provider: anthropic
model: claude-sonnet-4-6
temperature: 0.3
max_tokens: 4096
```

Note:

- Quando `thinking_effort` è configurato (solo Anthropic, attualmente Decision Maker con Opus 4.7), `temperature` viene ignorata: Opus 4.7 non accetta `temperature` con thinking abilitato. L'interfaccia estrae automaticamente solo i blocchi `text` dalla risposta, scartando i blocchi `thinking`.
- Per Anthropic senza `thinking_effort` (Performance Reviewer, Sonnet 4.6) il comportamento resta quello classico: `temperature` applicata, niente thinking.
- Per Gemini 3.x (Risk Manager con `gemini-3.1-pro-preview`), `temperature` è volutamente omessa: Google raccomanda esplicitamente di lasciare il parametro al default `1.0` e di non impostarlo a valori bassi sui modelli reasoning, dove può causare comportamenti degradati o loop. L'interfaccia `GeminiInterface` accetta ancora `temperature` come parametro opzionale — se valorizzato, viene inoltrato — ma il file di configurazione non lo imposta.
- `max_tokens` limita la lunghezza massima della risposta del modello. Per il Decision Maker il valore è alzato a `16384` perché con `thinking_effort` abilitato il budget è condiviso tra thinking interno e output finale: un limite troppo basso satura il budget.

### `config/prompts/`

Prompt runtime caricati dal codice durante l'esecuzione. Ogni agente ha il suo file markdown.

- `market_analyst.md` — Prompt operativo del Market Analyst
- `decision_maker.md` — Prompt operativo del Decision Maker
- `risk_manager.md` — Prompt operativo del Risk Manager
- `performance_reviewer.md` — Prompt operativo del Performance Reviewer

I file in `dev_support/prompts/` sono la versione di progettazione e riferimento umano. Quelli in `config/prompts/` sono la versione usata dal codice.

---

## Distinzione tra `config/` e `.env`

| Cosa                          | Dove        |
|-------------------------------|-------------|
| Chiavi API, URL, segreti      | `.env`      |
| Modalità di esecuzione        | `.env`      |
| Modello LLM, temperature      | `config/`   |
| Prompt degli agenti           | `config/`   |
| Regole operative (min order)  | `config/`   |
| Simbolo di trading            | `config/`   |

---

## 🧪 Testing

Test automatici per il caricamento della configurazione:

```bash
pytest tests/utils/test_config.py -v
```

Verifica manuale delle connessioni API (Binance, OpenAI, Gemini, Claude, Telegram):

```bash
python dev_support/verify_connections.py
```

---

## 🔍 Troubleshooting

### Problema: `ValueError: Missing required environment variable: TRADING_MODE`

**Causa**: la variabile `TRADING_MODE` non è presente nel `.env` (oppure è vuota).
**Soluzione**: aggiungere `TRADING_MODE=DEMO` o `TRADING_MODE=REAL` nel file `.env`.

### Problema: `ValueError: Missing required environment variable: CYCLE_INTERVAL_SECONDS`

**Causa**: la variabile `CYCLE_INTERVAL_SECONDS` non è presente nel `.env` (oppure è vuota).
**Soluzione**: aggiungere `CYCLE_INTERVAL_SECONDS=300` (o l'intervallo desiderato in secondi) nel file `.env`.

### Problema: `ValueError` su `TRADING_MODE` con valore non valido

**Causa**: `TRADING_MODE` ha un valore diverso da `DEMO` o `REAL` (es. `demo`, `test`, `live`). Il valore è case-sensitive.
**Soluzione**: usare esattamente `DEMO` o `REAL` in maiuscolo.

### Problema: `ValueError: Invalid boolean value` su `KILL_SWITCH`

**Causa**: `KILL_SWITCH` ha un valore non riconosciuto. Valori accettati: `1`, `true`, `yes`, `on`, `0`, `false`, `no`, `off`.
**Soluzione**: usare uno dei valori accettati (es. `KILL_SWITCH=1`).

### Problema: `FileNotFoundError: File di configurazione non trovato`

**Causa**: manca uno dei file YAML nella cartella `config/` (`trading.yaml`, `symbols.yaml`, o uno dei file in `llm_models/`).
**Soluzione**: verificare che tutti i file YAML siano presenti nella cartella `config/`. Se il progetto è stato clonato di recente, questi file dovrebbero essere già nel repository.

### Problema: `ValueError: Campo 'symbol' mancante in symbols.yaml`

**Causa**: il file `config/symbols.yaml` esiste ma non contiene il campo `symbol`.
**Soluzione**: aggiungere `symbol: BTCUSDC` (o il simbolo desiderato) nel file.

### Problema: `ValueError: Campo 'quote_currency' mancante in symbols.yaml`

**Causa**: il file `config/symbols.yaml` esiste ma non contiene il campo `quote_currency`.
**Soluzione**: aggiungere `quote_currency: USDC` (o la quote currency corrispondente al simbolo).

### Problema: `KeyError: 'model'` all'avvio

**Causa**: uno dei file YAML in `config/llm_models/` non contiene il campo `model`.
**Soluzione**: verificare che ogni file YAML abbia almeno il campo `model` con il nome del modello (es. `model: claude-sonnet-4-6`).

---

## 📚 Riferimenti

- **Codice**: `src/utils/config.py`
- **Test**: `tests/utils/test_config.py`
- **Verifica connessioni**: `dev_support/verify_connections.py`
- **File di esempio**: `.env.example`
- **Doc correlati**: `docs/architecture.md`
