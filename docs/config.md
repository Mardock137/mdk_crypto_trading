# ⚙️ Configurazione

Il sistema usa due fonti di configurazione separate: il file `.env` per i segreti e la cartella `config/` per le configurazioni applicative.

## `.env` — Segreti e variabili d'ambiente

Contiene chiavi API, modalità di esecuzione e variabili riservate. Mai committato su git.

| Variabile                 | Obbligatoria | Default  | Descrizione                                       |
|---------------------------|--------------|----------|---------------------------------------------------|
| `TRADING_MODE`            | sì           | —        | `DEMO` o `REAL`                                   |
| `KILL_SWITCH`             | no           | `1`      | Se `1`, forza tutte le operazioni a HOLD          |
| `CYCLE_INTERVAL_SECONDS`  | sì           | —        | Secondi tra un ciclo e l'altro                    |
| `LOG_LEVEL`               | no           | `INFO`   | `DEBUG`, `INFO`, `WARNING`, `ERROR`               |
| `OPENAI_API_KEY`          | no           | —        | Chiave API OpenAI                                 |
| `GEMINI_API_KEY`          | no           | —        | Chiave API Google Gemini                          |
| `BINANCE_API_KEY`         | in REAL      | —        | Chiave API Binance produzione                     |
| `BINANCE_SECRET_KEY`      | in REAL      | —        | Secret Binance produzione                         |
| `BINANCE_DEMO_API_KEY`    | in DEMO      | —        | Chiave API Binance Demo Trading                   |
| `BINANCE_DEMO_SECRET_KEY` | in DEMO      | —        | Secret Binance Demo Trading                       |
| `BINANCE_DEMO_BASE_URL`   | in DEMO      | —        | URL Binance Demo (`https://demo-api.binance.com`) |

Vedi `.env.example` per un template completo.

## `config/` — Configurazioni applicative

### `config/trading.yaml`

Regole operative statiche del sistema.

```yaml
min_order_usdc: 10.0
```

### `config/symbols.yaml`

Simbolo di trading attivo.

```yaml
symbol: BTCUSDC
```

### `config/llm_models/`

Configurazione dei modelli LLM usati dagli agenti. Un file YAML per agente.

**`market_analyst.yaml`:**

```yaml
provider: openai
model: gpt-5.4
temperature: 0.2
max_tokens: 512
```

I parametri `temperature` e `max_tokens` vengono passati direttamente al client LLM.

### `config/prompts/`

Prompt runtime caricati dal codice durante l'esecuzione. Ogni agente ha il suo file markdown.

- `market_analyst.md` — Prompt operativo del Market Analyst

I file in `dev_support/prompts/` sono la versione di progettazione e riferimento umano. Quelli in `config/prompts/` sono la versione usata dal codice.

## Distinzione tra `config/` e `.env`

| Cosa                          | Dove        |
|-------------------------------|-------------|
| Chiavi API, URL, segreti      | `.env`      |
| Modalità di esecuzione        | `.env`      |
| Modello LLM, temperature      | `config/`   |
| Prompt degli agenti           | `config/`   |
| Regole operative (min order)  | `config/`   |
| Simbolo di trading            | `config/`   |
