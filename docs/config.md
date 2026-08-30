# Configuration

The system uses two separate configuration sources: the `.env` file for secrets and the `config/` folder for application configuration.

---

## 📋 Table of Contents

- [`.env` — Secrets and environment variables](#env--secrets-and-environment-variables)
- [`config/` — Application configuration](#config--application-configuration)
- [Distinction between `config/` and `.env`](#distinction-between-config-and-env)
- [🧪 Testing](#-testing)
- [🔍 Troubleshooting](#-troubleshooting)
- [📚 References](#-references)

---

## `.env` — Secrets and environment variables

Contains API keys, execution mode and confidential variables. Never committed to git.

| Variable                  | Required | Default  | Description                                       |
|---------------------------|----------|----------|---------------------------------------------------|
| `TRADING_MODE`            | yes      | —        | `DEMO` or `REAL`                                  |
| `KILL_SWITCH`             | no       | `1`      | If `1`, forces all operations to HOLD             |
| `CYCLE_INTERVAL_SECONDS`  | yes      | —        | Seconds between one cycle and the next            |
| `LOG_LEVEL`               | no       | `INFO`   | `DEBUG`, `INFO`, `WARNING`, `ERROR`               |
| `CLAUDE_API_KEY`          | yes      | —        | Anthropic (Claude) API key                        |
| `OPENAI_API_KEY`          | yes      | —        | OpenAI API key                                    |
| `GEMINI_API_KEY`          | yes      | —        | Google Gemini API key                             |
| `BINANCE_API_KEY`         | in REAL  | —        | Binance production API key                        |
| `BINANCE_SECRET_KEY`      | in REAL  | —        | Binance production secret                         |
| `BINANCE_DEMO_API_KEY`    | in DEMO  | —        | Binance Demo Trading API key                      |
| `BINANCE_DEMO_SECRET_KEY` | in DEMO  | —        | Binance Demo Trading secret                       |
| `BINANCE_DEMO_BASE_URL`   | in DEMO  | —        | Binance Demo URL (`https://demo-api.binance.com`) |
| `TELEGRAM_BOT_TOKEN`      | no       | —        | Telegram bot token (optional notifications)       |
| `TELEGRAM_CHAT_ID`        | no       | —        | Target Telegram chat ID                           |
| `ALPHA_VANTAGE_API_KEY`   | no       | —        | Alpha Vantage API key (crypto news)               |

See `.env.example` for a complete template.

---

## `config/` — Application configuration

### `config/trading.yaml`

Static operational rules of the system and the investment mandate.

```yaml
min_order_usdc: 10.0
max_order_notional_usdc: 500.0
breakeven_trigger_pct: 2.0
oco_review_interval_hours: 24.0

mandate:
  max_drawdown_pct: 15.0
  horizon: "Intraday to swing (hours → days)"
  max_position_pct: 70.0

circuit_breaker:
  threshold: 3
  log_interval_seconds: 3600

memory_compaction:
  threshold: 5000
  keep_last_n: 100
```

Fields:

- `min_order_usdc`: minimum notional threshold (quantity × price) allowed for a single order, in USDC. The guardrail in `ExecutionTraderAgent` blocks any order whose notional is below this value, returning `NOT_EXECUTED` with a reason tracked in the event logs — mirroring the maximum guardrail (`max_order_notional_usdc`). Defense in depth: it complements (does not replace) Binance's `minNotional` filter.
- `max_order_notional_usdc`: maximum notional value (quantity × price) allowed for a single order, in USDC. The guardrail in `ExecutionTraderAgent` blocks any order whose notional exceeds this limit, returning `NOT_EXECUTED` with a reason tracked in the event logs. The software fallback (if the field is missing from the file) is `500.0`.
- `breakeven_trigger_pct`: unrealized profit threshold (in percentage) above which the runner automatically moves the Stop Loss of the active OCO to the entry price (breakeven). The mechanism is deterministic, runs before the LLM chain and does not involve the Decision Maker. It does not run if the kill switch is active (`KILL_SWITCH=1`). The software fallback is `2.0`.
- `oco_review_interval_hours`: hours elapsed since an OCO was opened beyond which the runner sets `oco_review_required = True` in the current cycle. When the flag is `True`, the Decision Maker's prompt makes explicit evaluation of the TP/SL levels mandatory. The software fallback is `24.0`.
- `mandate.max_drawdown_pct`: maximum tolerated drawdown, in percentage.
- `mandate.horizon`: typical time horizon of the trades (e.g. intraday, swing).
- `mandate.max_position_pct`: maximum percentage of capital allocatable to a single position. The guardrail in `ExecutionTraderAgent` computes the percentage against the **total portfolio value** (total USDC, free + locked in open orders, plus the total value of the coins). The field already exists in anticipation of multi-symbol support.
- `circuit_breaker.threshold`: number of identical consecutive errors after which the system stops and sends the Telegram alert. The software fallback (if the field is missing) is `3`.
- `circuit_breaker.log_interval_seconds`: how often, in seconds, the "system stopped, restart manually" reminder is written to the logs while the circuit breaker is tripped. The software fallback is `3600`.
- `memory_compaction.threshold`: number of records in the memory's JSONL file beyond which compaction is automatically run at runner startup. With 5-minute cycles, this corresponds to roughly 17 days of history. The software fallback is `5000`.
- `memory_compaction.keep_last_n`: how many real records to keep after compaction. BUY lots still open within the removed window are preserved as synthetic records to keep the FIFO calculation correct. Must be >= 10 (the minimum used by `get_memory`). The software fallback is `100`.

The mandate is loaded at runner startup via `load_mandate(trading_config)` in `src/utils/config.py` and propagated on every cycle inside `TradingCycleInput`. If the `mandate` section is missing or has incomplete fields, the runner fails at boot with an explicit `ValueError`.

### `config/cycle_skip.yaml`

Configuration of the **deterministic pre-check** that decides whether to skip an operational cycle when the market context has remained substantially identical to the previous one. Goal: avoid calling Analyst + Decision Maker (Opus with thinking) + Risk Manager when there are no significant changes, saving tokens and latency.

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

Fields:

- `enabled`: if `false`, the pre-check is disabled and every cycle runs the full agent chain (pre-feature behavior).
- `max_consecutive_skips`: after N consecutive skips, the next cycle always runs in full (even if the context is unchanged). Prevents getting "stuck" in an infinite skip.
- `thresholds.price_delta_pct`: maximum percentage price change between the previous and current cycle (beyond it → no skip).
- `thresholds.rsi_delta`: maximum absolute RSI change (beyond it → no skip).
- `thresholds.macd_sign_must_match`: if `true`, the sign of `macd - macd_signal` must match the previous cycle; a flip prevents the skip.
- `thresholds.require_no_order_events`: if `true`, any change in the set of open orders (new order, fill, cancellation) prevents the skip.
- `thresholds.require_previous_action_hold`: if `true`, skipping is only allowed if the previous cycle's action was `HOLD`.

If the file is missing, the system applies a safe fallback with `enabled=false` (no cycle is skipped). The previous context's snapshot lives only in the runner's memory: after every restart, the first cycle is always full.

### `config/symbols.yaml`

Active trading symbol and quote currency.

```yaml
symbol: BTCUSDC
quote_currency: USDC
```

- `symbol`: active trading pair (e.g. `BTCUSDC`, `ETHUSDC`)
- `quote_currency`: reference currency used to compute balances and value. Must match the symbol's suffix

### `config/news.yaml`

Crypto news source configuration.

```yaml
source: alpha_vantage
interval_hours: 12        # NewsReviewRunner cadence (gate on the report file)
query:
  topics: blockchain      # general crypto coverage
  tickers: ""             # empty: no strict filter, also captures systemic news
  lookback_hours: 12
  max_articles: 50
  sort: LATEST
```

Fields:

- `source`: identifier of the active news source (currently only `alpha_vantage`).
- `interval_hours`: how often, in hours, the `NewsReviewRunner` should run a new review. The gate is based on the most recent report file in `data/news_reports/`: if it is more recent than `interval_hours`, the cycle proceeds without calling the client. Software default: `12`.
- `query.topics`: news category to request from Alpha Vantage (e.g. `blockchain`). Covers crypto news in general, not limited to BTC.
- `query.tickers`: filter for specific tickers (e.g. `CRYPTO:BTC`). If empty, no strict filter: systemic news is also received.
- `query.lookback_hours`: time window in hours for the call (computes `time_from = UTC now - lookback_hours`). Also used as `hours_analyzed` in the markdown report.
- `query.max_articles`: maximum number of articles to request from Alpha Vantage (`limit` parameter).
- `query.sort`: article sort order (`LATEST`, `EARLIEST`, `RELEVANCE`).

The file is read by `load_news_config()` in `src/utils/config.py`. If the file is missing, the function returns an empty dict with no errors (safe fallback).

### `config/llm_models/`

Configuration of the LLM models used by the agents. One YAML file per agent.

**`market_analyst.yaml`** (provider: OpenAI):

```yaml
provider: openai
model: gpt-5.6-terra
reasoning_effort: medium
max_tokens: 4096
```

**`decision_maker.yaml`** (provider: Anthropic, with adaptive thinking):

```yaml
provider: anthropic
model: claude-opus-5
thinking_effort: medium
max_tokens: 16384
```

**`risk_manager.yaml`** (provider: Gemini):

```yaml
provider: gemini
model: gemini-3.7-flash
max_tokens: 4096
```

**`news_reviewer.yaml`** (provider: Anthropic):

```yaml
provider: anthropic
model: claude-sonnet-5
thinking_effort: medium
max_tokens: 4096
```

**`performance_reviewer.yaml`** (provider: Anthropic):

```yaml
provider: anthropic
model: claude-sonnet-5
thinking_effort: medium
max_tokens: 4096
```

Notes:

- GPT-5.6 Terra and Claude Sonnet 5 are models with adaptive thinking/reasoning enabled by default: they reject `temperature` with any value other than the default (400 error from the API). For this reason, Market Analyst, Decision Maker, Performance Reviewer and News Reviewer all use `reasoning_effort` (OpenAI) or `thinking_effort` (Anthropic) instead of `temperature`. The Anthropic interface automatically extracts only the `text` blocks from the response, discarding the `thinking` blocks.
- The logic is generic and applies to any agent on these two providers: if `reasoning_effort`/`thinking_effort` is set in the YAML, `temperature` is ignored regardless of its value (even if present in the file, it would never be sent to the API). The "classic" behavior with `temperature` sent still applies to Anthropic/OpenAI only for an agent whose YAML does not set `reasoning_effort`/`thinking_effort` (none, currently, in this project).
- For Gemini 3.x (Risk Manager with `gemini-3.7-flash`), `temperature` is deliberately omitted: Google explicitly recommends leaving the parameter at its default and not setting it to low values on reasoning models, where it can cause degraded behavior or loops. The `GeminiInterface` still accepts `temperature` as an optional parameter — if set, it is forwarded — but the configuration file does not set it.
- `max_tokens` limits the maximum length of the model's response. For the Decision Maker, the value is raised to `16384` because with `thinking_effort` enabled, the budget is shared between internal thinking and the final output: a limit that is too low saturates the budget.

### `config/prompts/`

Runtime prompts loaded by the code during execution. Each agent has its own markdown file.

- `market_analyst.md` — Market Analyst operational prompt
- `decision_maker.md` — Decision Maker operational prompt
- `risk_manager.md` — Risk Manager operational prompt
- `performance_reviewer.md` — Performance Reviewer operational prompt
- `news_reviewer.md` — News Reviewer operational prompt

---

## Distinction between `config/` and `.env`

| What                           | Where       |
|--------------------------------|-------------|
| API keys, URLs, secrets        | `.env`      |
| Execution mode                 | `.env`      |
| LLM model, temperature         | `config/`   |
| Agent prompts                  | `config/`   |
| Operational rules (min order)  | `config/`   |
| Trading symbol                 | `config/`   |

---

## 🧪 Testing

Automated tests for configuration loading:

```bash
pytest tests/utils/test_config.py -v
```

Manual verification of API connections (Binance, OpenAI, Gemini, Claude, Telegram, Alpha Vantage):

```bash
python verify_connections.py
```

---

## 🔍 Troubleshooting

### Problem: `ValueError: Missing required environment variable: TRADING_MODE`

**Cause**: the `TRADING_MODE` variable is not present in `.env` (or is empty).
**Solution**: add `TRADING_MODE=DEMO` or `TRADING_MODE=REAL` to the `.env` file.

### Problem: `ValueError: Missing required environment variable: CYCLE_INTERVAL_SECONDS`

**Cause**: the `CYCLE_INTERVAL_SECONDS` variable is not present in `.env` (or is empty).
**Solution**: add `CYCLE_INTERVAL_SECONDS=300` (or the desired interval in seconds) to the `.env` file.

### Problem: `ValueError` on `TRADING_MODE` with an invalid value

**Cause**: `TRADING_MODE` has a value other than `DEMO` or `REAL` (e.g. `demo`, `test`, `live`). The value is case-sensitive.
**Solution**: use exactly `DEMO` or `REAL` in uppercase.

### Problem: `ValueError: Invalid boolean value` on `KILL_SWITCH`

**Cause**: `KILL_SWITCH` has an unrecognized value. Accepted values: `1`, `true`, `yes`, `on`, `0`, `false`, `no`, `off`.
**Solution**: use one of the accepted values (e.g. `KILL_SWITCH=1`).

### Problem: `FileNotFoundError: Configuration file not found`

**Cause**: one of the YAML files in the `config/` folder is missing (`trading.yaml`, `symbols.yaml`, or one of the files in `llm_models/`).
**Solution**: verify that all YAML files are present in the `config/` folder. If the project was recently cloned, these files should already be in the repository.

### Problem: `ValueError: Missing 'symbol' field in symbols.yaml`

**Cause**: the `config/symbols.yaml` file exists but does not contain the `symbol` field.
**Solution**: add `symbol: BTCUSDC` (or the desired symbol) to the file.

### Problem: `ValueError: Missing 'quote_currency' field in symbols.yaml`

**Cause**: the `config/symbols.yaml` file exists but does not contain the `quote_currency` field.
**Solution**: add `quote_currency: USDC` (or the quote currency matching the symbol).

### Problem: `KeyError: 'model'` at startup

**Cause**: one of the YAML files in `config/llm_models/` does not contain the `model` field.
**Solution**: verify that every YAML file has at least the `model` field with the model name (e.g. `model: claude-sonnet-5`).

---

## 📚 References

- **Code**: `src/utils/config.py`
- **Tests**: `tests/utils/test_config.py`
- **Connection check**: `verify_connections.py`
- **Example file**: `.env.example`
- **Related docs**: `docs/architecture.md`
