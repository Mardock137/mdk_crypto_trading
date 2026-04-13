# Observability - Sistema di Logging

MDK Crypto Trading produce due tipi di log complementari: un log testuale per il monitoraggio operativo e un log JSON strutturato per l'analisi delle decisioni ciclo per ciclo.

---

## 📋 Indice

- [Log testuale (`logs/mdk_crypto_trading.log`)](#log-testuale-logsmdk_crypto_tradinglog)
- [Log eventi JSON (`logs/events/`)](#log-eventi-json-logsevents)
- [Struttura della cartella `logs/`](#struttura-della-cartella-logs)
- [🔧 Configurazione](#-configurazione)
- [📱 Notifiche Telegram](#-notifiche-telegram)
- [Come leggere i log eventi](#come-leggere-i-log-eventi)
- [🧪 Testing](#-testing)
- [📚 Riferimenti](#-riferimenti)

---

## Log testuale (`logs/mdk_crypto_trading.log`)

Output leggibile destinato al monitoraggio in tempo reale e al debug.

- **Console**: output colorato tramite Rich (o StreamHandler come fallback)
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
  "timestamp": "2026-03-24T14:30:00",
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
  "timestamp": "2026-03-24T14:30:00",
  "symbol": "BTCUSDC",
  "trading_mode": "DEMO",
  "market_analysis": null,
  "trade_proposal": null,
  "risk_assessment": null,
  "execution_report": null,
  "error": "Connessione a Binance fallita: timeout"
}
```

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

| Notifica              | Quando scatta                                   |
|-----------------------|-------------------------------------------------|
| 🚀 **Bot STARTED**    | All'avvio del runner                            |
| ✅ **Order EXECUTED** | Quando un ordine viene eseguito su Binance      |
| ⚠️ **Cycle ERROR**    | Se un ciclo operativo fallisce con un'eccezione |
| 🛑 **Bot STOPPED**    | Allo stop del sistema (Ctrl+C o `docker stop`)  |

**Esempio notifica ordine eseguito:**

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

## 🧪 Testing

```bash
pytest tests/utils/test_logging_config.py -v
pytest tests/utils/test_event_logger.py -v
```

---

## 📚 Riferimenti

- **Codice**: `src/utils/logging_config.py`, `src/utils/event_logger.py`, `src/utils/telegram_notifier.py`
- **Test**: `tests/utils/test_logging_config.py`, `tests/utils/test_event_logger.py`, `tests/utils/test_telegram_notifier.py`
- **Doc correlati**: `docs/architecture.md`, `docs/config.md`
