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
| `CLAUDE_API_KEY`          | no           | —        | Chiave API Anthropic (Claude)                     |
| `OPENAI_API_KEY`          | no           | —        | Chiave API OpenAI                                 |
| `GEMINI_API_KEY`          | no           | —        | Chiave API Google Gemini                          |
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

mandate:
  objective: "Generare rendimento sul capitale"
  min_monthly_return_pct: 2.0
  max_drawdown_pct: 15.0
  horizon: "Intraday to swing (ore → giorni)"
  max_position_pct: 100.0
  min_trades_per_week: 3
```

Campi:

- `min_order_usdc`: valore minimo interno consentito per un ordine, in USDC.
- `mandate.objective`: descrizione testuale dell'obiettivo strategico del sistema.
- `mandate.min_monthly_return_pct`: rendimento mensile minimo atteso in percentuale.
- `mandate.max_drawdown_pct`: drawdown massimo tollerato in percentuale.
- `mandate.horizon`: orizzonte temporale tipico delle operazioni (es. intraday, swing).
- `mandate.max_position_pct`: percentuale massima del capitale allocabile sulla singola posizione. Finché il bot è mono-simbolo è tipicamente `100.0`; il campo esiste già in vista del multi-simbolo.
- `mandate.min_trades_per_week`: numero minimo di trade attesi per settimana. È usato dal Decision Maker come indicatore per evitare di ripiegare su `HOLD` "nel dubbio".

Il mandate viene caricato all'avvio del runner tramite `load_mandate(trading_config)` in `src/utils/config.py` e propagato a ogni ciclo dentro `TradingCycleInput`. Se la sezione `mandate` manca o ha campi incompleti, il runner fallisce in fase di boot con un `ValueError` esplicito.

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

**`market_analyst.yaml`** (provider: Anthropic):

```yaml
provider: anthropic
model: claude-sonnet-4-6
temperature: 0.2
max_tokens: 2048
```

**`decision_maker.yaml`** (provider: OpenAI):

```yaml
provider: openai
model: gpt-5.4
reasoning_effort: high
temperature: 0.2
max_tokens: 8192
```

**`risk_manager.yaml`** (provider: Gemini):

```yaml
provider: gemini
model: gemini-3.1-pro-preview
temperature: 0.2
max_tokens: 2048
```

Note:

- Quando `reasoning_effort` è configurato (solo OpenAI, Decision Maker), `temperature` viene ignorata perché GPT-5.4 non li accetta insieme.
- `max_tokens` limita la lunghezza massima della risposta del modello. Per il Decision Maker il valore è alzato a `8192` perché con `reasoning_effort: high` i reasoning tokens interni consumano una quota significativa del budget: un limite troppo basso satura il budget e produce risposte vuote (`finish_reason: length`).

### `config/prompts/`

Prompt runtime caricati dal codice durante l'esecuzione. Ogni agente ha il suo file markdown.

- `market_analyst.md` — Prompt operativo del Market Analyst
- `decision_maker.md` — Prompt operativo del Decision Maker
- `risk_manager.md` — Prompt operativo del Risk Manager

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
