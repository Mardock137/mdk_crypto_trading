# Observability - Sistema di Logging

MDK Crypto Trading produce due tipi di log complementari: un log testuale per il monitoraggio operativo e un log JSON strutturato per l'analisi delle decisioni ciclo per ciclo.

---

## 📋 Indice

- [Log testuale (`logs/mdk_crypto_trading.log`)](#log-testuale-logsmdk_crypto_tradinglog)
- [Log eventi JSON (`logs/events/`)](#log-eventi-json-logsevents)
- [Report performance (`data/performance_reports/`)](#report-performance-dataperformance_reports)
- [Heartbeat Docker (`data/heartbeat`)](#heartbeat-docker-dataheartbeat)
- [Struttura della cartella `logs/`](#struttura-della-cartella-logs)
- [🔧 Configurazione](#-configurazione)
- [📱 Notifiche Telegram](#-notifiche-telegram)
- [Come leggere i log eventi](#come-leggere-i-log-eventi)
- [🧪 Testing](#-testing)
- [📚 Riferimenti](#-riferimenti)

---

## Log testuale (`logs/mdk_crypto_trading.log`)

Output leggibile destinato al monitoraggio in tempo reale e al debug.

- **Console**: output colorato tramite Rich (o StreamHandler come fallback). I traceback Rich sono disabilitati (`rich_tracebacks=False`) per mantenere la console Docker compatta; il traceback completo è sempre presente nel file di log.
- **File**: `logs/mdk_crypto_trading.log` con rotazione automatica
  - Rotazione al raggiungimento di 5 MB
  - Vengono mantenuti gli ultimi 5 file storici (`.log.1`, `.log.2`, ecc.)
  - Encoding UTF-8

**Formato delle righe:**

```log
2026-03-24 14:30:00,123 | INFO | mdk_crypto_trading | Messaggio di esempio
```

**Livelli disponibili** (configurabile via `LOG_LEVEL` nel `.env`):

| Livello   | Quando usarlo                                     |
|-----------|---------------------------------------------------|
| `DEBUG`   | Dettagli interni, utile durante lo sviluppo       |
| `INFO`    | Flusso operativo normale (default)                |
| `WARNING` | Situazioni anomale ma non bloccanti               |
| `ERROR`   | Errori che impediscono il completamento del ciclo |

---

## Log eventi JSON (`logs/events/`)

Log strutturato che registra le decisioni di ogni ciclo operativo in formato machine-readable.

- Un file `.jsonl` per giorno (es. `2026-03-24.jsonl`)
- Ogni riga è un oggetto JSON autonomo (formato JSON Lines)
- La cartella viene creata automaticamente se non esiste

### Ciclo completato con successo

```json
{
  "timestamp": "2026-03-24T14:30:00+00:00",
  "symbol": "BTCUSDC",
  "trading_mode": "DEMO",
  "market_analysis": { "market_bias": "BULLISH", "signal_strength": 0.78, "confidence": 0.74, "..." : "..." },
  "trade_proposal": { "action": "BUY", "order_type": "MARKET", "confidence": 0.82, "..." : "..." },
  "risk_assessment": { "risk_decision": "APPROVE", "confidence": 0.91, "..." : "..." },
  "execution_report": { "execution_status": "EXECUTED", "executed_action": "BUY", "..." : "..." },
  "error": null
}
```

### Ciclo fallito con errore

```json
{
  "timestamp": "2026-03-24T14:30:00+00:00",
  "symbol": "BTCUSDC",
  "trading_mode": "DEMO",
  "market_analysis": { "market_bias": "BULLISH", "..." : "..." },
  "trade_proposal": { "action": "BUY", "..." : "..." },
  "risk_assessment": null,
  "execution_report": null,
  "error": "Risk Manager failed: Risposta vuota dal provider",
  "correlation_id": "a1b2c3d4"
}
```

Il campo `correlation_id` è un token esadecimale di 8 caratteri generato dal runner al momento dell'eccezione. Permette di collegare il record JSONL, la riga `ERROR` nel log testuale (che include il traceback completo) e la notifica Telegram di errore, senza esporre il dettaglio dell'eccezione fuori dai log interni.

Se l'errore avviene a metà del workflow (es. Risk Manager fallisce dopo che Market Analyst e Decision Maker hanno già prodotto i loro output), i campi `market_analysis`, `trade_proposal` e/o `risk_assessment` contengono i risultati parziali già ottenuti per consentire il debug post-mortem. Gli step non ancora raggiunti restano a `null`. Per gli errori avvenuti fuori dal workflow (es. fetch market data) tutti e quattro i campi restano a `null`.

### Ciclo skippato dal pre-check deterministico

```json
{
  "timestamp": "2026-03-24T14:30:00+00:00",
  "symbol": "BTCUSDC",
  "trading_mode": "DEMO",
  "cycle_type": "skipped",
  "reason": "Contesto invariato rispetto al ciclo precedente",
  "snapshot": {
    "price": 84521.30,
    "rsi": 54.2,
    "macd": 12.5,
    "macd_signal": 11.8,
    "previous_action": "HOLD",
    "open_order_ids": []
  },
  "error": null
}
```

I record con `cycle_type: "skipped"` non contengono i payload degli agenti (`market_analysis`, `trade_proposal`, ecc.) perché la catena LLM non è stata eseguita. Vengono generati da `EventLogger.log_skipped_cycle()` quando il `CycleSkipHandler` decide di saltare il ciclo. Configurazione dello skip in `config/cycle_skip.yaml` (vedi `docs/config.md`).

---

## Report performance (`data/performance_reports/`)

Il `Performance Reviewer` genera **un report markdown al giorno** sintetico e leggibile dal Chief, salvato in `data/performance_reports/YYYY-MM-DD.md`.

Ogni report contiene:

- Sintesi testuale del Reviewer (giudizio LLM, max 400 caratteri)
- Aderenza al mandato: `ALIGNED`, `DRIFTING` o `MISALIGNED`
- Mandato operativo di riferimento (drawdown massimo, orizzonte, posizione massima)
- Statistiche deterministiche calcolate in Python (zero LLM): cicli totali, HOLD ratio, BUY/SELL eseguiti, SELL falliti, segnali forti ignorati, giorni senza trade eseguito, P&L realizzato e medio percentuale
- 1-3 suggerimenti concreti per il Decision Maker

Questo stesso file viene letto dal DM nei cicli successivi (campo `latest_performance_review`). La cartella `data/` è ignorata da git: i report restano locali alla VM.

Il trigger è giornaliero: se il file del giorno esiste già, il Reviewer non viene chiamato (zero costo LLM).

---

## Heartbeat Docker (`data/heartbeat`)

Il runner scrive il file `data/heartbeat` come **prima operazione di ogni ciclo** (inclusi i cicli skippati dal `CycleSkipHandler`). Il contenuto è il timestamp UTC ISO 8601 dell'ultimo ciclo avviato, ad esempio:

```text
2026-04-29T14:30:00+00:00
```

Questo file non ha valore di osservabilità diretta per il Chief, ma è usato dal `HEALTHCHECK` Docker: se il file non viene aggiornato entro 180 minuti, Docker marca il container come `unhealthy` (visibile con `docker compose ps`).

> **Nota**: il file viene creato alla prima esecuzione. Se non esiste ancora (container appena avviato), Docker applica il `start-period` di 5 minuti prima di iniziare i controlli.

---

## Struttura della cartella `logs/`

```text
logs/
├── mdk_crypto_trading.log          # Log testuale con rotazione
├── mdk_crypto_trading.log.1        # Backup rotazione (più recente)
├── mdk_crypto_trading.log.2        # ...
└── events/
    ├── 2026-03-24.jsonl            # Un file al giorno
    └── 2026-03-25.jsonl
```

---

## 🔧 Configurazione

| Variabile   | Dove       | Default  | Descrizione                  |
|-------------|------------|----------|------------------------------|
| `LOG_LEVEL` | `.env`     | `INFO`   | Livello minimo dei log       |

La cartella `logs/` è già presente nel `.gitignore` e non viene tracciata.

---

## 📱 Notifiche Telegram

Il sistema invia notifiche opzionali via Telegram Bot API. Se `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` non sono configurati nel `.env`, le notifiche sono silenziosamente disabilitate.

| Notifica                          | Quando scatta                                                                                                                                           |
|-----------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| 🚀 **Bot STARTED**                | All'avvio del runner                                                                                                                                    |
| ✅ **Order EXECUTED**             | Quando un ordine viene eseguito su Binance                                                                                                              |
| ⚠️ **Cycle ERROR**                | Se un ciclo operativo fallisce con un'eccezione                                                                                                         |
| 🚨 **CIRCUIT BREAKER TRIPPED**    | Dopo 3 errori identici consecutivi (vedi sezione "Circuit breaker")                                                                                     |
| 🔴 **[ALARM] POSIZIONE SCOPERTA** | Se un `CANCEL_AND_REPLACE` cancella l'ordine ma la sostituzione fallisce — la posizione rimane senza protezione e richiede intervento manuale immediato |
| 🛑 **Bot STOPPED**                | Allo stop del sistema (Ctrl+C o `docker stop`)                                                                                                          |

**Esempio notifica ordine eseguito (MARKET):**

```text
✅ Order EXECUTED

Action: BUY
Type: MARKET
Quantity: 0.00123
Price: 84521.30
Value: 103.96 USDC
DM Confidence: 0.82
Symbol: BTCUSDC
Mode: DEMO
```

**Esempio notifica ordine eseguito (SELL_OCO):**

```text
✅ Order EXECUTED

Action: SELL_OCO
Type: LIMIT
Quantity: 0.003
TP Price: 87000.00
SL Stop: 79000.00
Est. Value: 261.00 USDC
DM Confidence: 0.79
Symbol: BTCUSDC
Mode: DEMO
```

**Esempio notifica posizione scoperta:**

```text
[ALARM] POSIZIONE SCOPERTA

Symbol: BTCUSDC
Mode: REAL
Ordine cancellato: 123456789

Stop loss / take profit non più attivo.
Intervenire manualmente sull'exchange.
```

**Esempio notifica errore ciclo:**

```text
⚠️ Cycle ERROR

Symbol: BTCUSDC
Categoria: API esterna non disponibile
Error ID: a1b2c3d4
```

Le categorie possibili sono:

| Categoria                     | Causa tipica                            | Azione                                                   |
|-------------------------------|-----------------------------------------|----------------------------------------------------------|
| `API esterna non disponibile` | Binance 502/503, Anthropic 529, timeout | Nessuna — il bot si recupera da solo al ciclo successivo |
| `Rate limit API`              | Codice 429 da qualsiasi provider        | Nessuna — il bot riprova automaticamente                 |
| `Risposta LLM non valida`     | JSON malformato o vuoto da un modello   | Monitorare — se ricorrente, indagare                     |
| `Errore interno`              | Bug nel codice, configurazione errata   | Controllare i log con l'Error ID                         |

La notifica non include `str(exc)` per evitare leak di dati sensibili (es. chiavi, URL con token). Il dettaglio completo dell'eccezione — incluso il traceback — è disponibile nel log file locale (`mdk_crypto_trading.log`) cercando la riga con `[cid=a1b2c3d4]`.

**Configurazione** (nel `.env`):

| Variabile            | Descrizione                                        |
|----------------------|----------------------------------------------------|
| `TELEGRAM_BOT_TOKEN` | Token del bot Telegram (fornito da @BotFather)     |
| `TELEGRAM_CHAT_ID`   | ID della chat o del canale che riceve le notifiche |

---

## Come leggere i log eventi

Per visualizzare i log JSON in modo leggibile da terminale:

```bash
# Ultimo ciclo registrato oggi
python -c "import json; print(json.dumps(json.loads(open('logs/events/2026-03-24.jsonl').readlines()[-1]), indent=2))"
```

Per analisi più avanzate, i file `.jsonl` possono essere caricati con `pandas`:

```python
import pandas as pd
df = pd.read_json("logs/events/2026-03-24.jsonl", lines=True)
```

---

## 🚨 Circuit breaker

Il `CircuitBreaker` (`src/core/circuit_breaker.py`) protegge il bot da loop di errori sistematici. Quando lo stesso errore (stesso tipo di eccezione + stesso messaggio) si verifica **3 volte di seguito**, il breaker scatta e il `TradingRunner`:

- smette di eseguire `_run_single_cycle` (nessuna chiamata LLM, nessun ordine Binance)
- continua ad aggiornare il file `data/heartbeat` (il container resta "healthy")
- invia una notifica Telegram **una sola volta**, nel momento in cui scatta
- logga un reminder nel log testuale **ogni ora** finché resta in pausa

Il breaker si resetta automaticamente dopo un ciclo riuscito (purché non sia ancora scattato): un errore transitorio non lo fa partire. Una volta scattato però NON si ripristina da solo: è una scelta voluta per forzare l'intervento umano.

**Come ripristinare:** riavvia il container.

```bash
docker compose restart trading-bot
```

**Signature degli errori:** la signature usata per il confronto è `f"{type(exc).__name__}:{str(exc)}"`. Per le `CycleExecutionError` (errori sollevati da `TradingWorkflow`) la signature usa l'eccezione originale (`exc.original`), non il wrapper.

**Esempio notifica Telegram:**

```text
[ALARM] CIRCUIT BREAKER TRIPPED

Symbol: BTCUSDC
Errori consecutivi: 3
Ultimo errore: LlmError:Risposta vuota dal provider OpenAI
Bot in pausa: richiede riavvio manuale (docker compose restart trading-bot)
```

---

## 🧪 Testing

```bash
pytest tests/utils/test_logging_config.py -v
pytest tests/utils/test_event_logger.py -v
```

---

## 📚 Riferimenti

- **Codice**: `src/utils/logging_config.py`, `src/utils/event_logger.py`, `src/utils/telegram_notifier.py`, `src/utils/log_utils.py`
- **Test**: `tests/utils/test_logging_config.py`, `tests/utils/test_event_logger.py`, `tests/utils/test_telegram_notifier.py`
- **Doc correlati**: `docs/architecture.md`, `docs/config.md`
