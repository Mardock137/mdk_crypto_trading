<!-- markdownlint-disable -->
# 📋 Changelog

## 1.4.2 — 2026-04-08

### Corretto

- `AnthropicInterface.generate_json()`: gestita la risposta con testo vuoto (`""`) — allineata al comportamento di `OpenAiInterface` e `GeminiInterface`. Prima, una risposta vuota causava `json.JSONDecodeError` e il ciclo falliva senza possibilità di retry

### Aggiunto

- 2 nuovi test in `tests/integrations/llm_interfaces/test_anthropic_interface.py`: risposta con testo vuoto e risposta senza content

---

## 1.4.1 — 2026-04-07

### Aggiunto

- `unwrap_llm_response()` in `src/agents/base_agent.py`: funzione helper che normalizza le risposte LLM prima del parsing — gestisce risposte wrappate in array (`[{...}]` → `{...}`), dict vuoti e tipi non attesi
- 6 nuovi test per `unwrap_llm_response` in `tests/agents/test_agent_interfaces.py`
- 2 nuovi test per ciascun parser (`test_risk_manager.py`, `test_decision_maker.py`, `test_market_analyst.py`): copertura su risposta array e risposta vuota

### Corretto

- Parsing risposte LLM nei 3 agenti (`_parse_risk_assessment`, `_parse_trade_proposal`, `_parse_market_analysis`): ora gestiscono correttamente risposte wrappate in array, che causavano errori in produzione con Gemini

---

## 1.4.0 — 2026-04-02

### Aggiunto

- `TelegramNotifier` (`src/utils/telegram_notifier.py`): nuovo componente per l'invio di notifiche Telegram tramite Bot API. Gestione errori silenziosa — nessuna eccezione propagata al bot in caso di problemi di rete o configurazione assente
- Notifiche integrate nel `TradingRunner` su 3 eventi: avvio del bot, stop (`Ctrl+C`), ordine eseguito (con dettagli: azione, tipo, quantità, prezzo, valore, confidenza) ed errore nel ciclo
- `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` aggiunti ad `AppSettings`, `load_settings()` e `.env.example` (entrambi opzionali)
- Test 7 (Telegram) in `dev_support/verify_connections.py`
- 6 nuovi test unitari in `tests/utils/test_telegram_notifier.py`
- 5 nuovi test nel runner (`tests/core/test_runner.py`): avvio, stop, errore, ordine eseguito, ordine non eseguito
- 1 nuovo test in `tests/test_main.py`: verifica che `TelegramNotifier` sia istanziato con le credenziali corrette
- 2 nuovi test in `tests/utils/test_config.py`: lettura variabili Telegram e default a `None` se assenti

### Modificato

- `src/core/runner.py`: aggiunto parametro opzionale `telegram_notifier: TelegramNotifier | None`
- `src/main.py`: bootstrap di `TelegramNotifier` e passaggio al runner
- Documentazione aggiornata: `config.md`, `repo_structure.md`, `architecture.md`, `README.md`

---

## 1.3.0 — 2026-04-01

### Aggiunto

- `Dockerfile`: immagine Docker basata su `python:3.12-slim` per il deploy in produzione
- `docker-compose.yaml`: configurazione del servizio `trading-bot` con volumi persistenti (`logs/`, `data/`) e `restart: unless-stopped`
- `.dockerignore`: esclude dal build context venv, cache, test, dev_support, docs, log, dati e file sensibili
- `docs/deploy.md`: guida completa al deploy su Google Compute Engine — creazione VM, installazione Docker, primo avvio, aggiornamenti, comandi utili e troubleshooting

### Modificato

- `docs/repo_structure.md`: aggiornato con i nuovi file (`Dockerfile`, `docker-compose.yaml`, `.dockerignore`, `docs/deploy.md`)
- `README.md`: aggiunto link a `docs/deploy.md` nella sezione Documentazione

---

## 1.2.0 — 2026-03-31

### Aggiunto

- `AnthropicInterface`: nuova interfaccia LLM per il provider Anthropic (Claude), con retry automatico via `tenacity` su errori temporanei
- `CLAUDE_API_KEY` in `AppSettings` e `load_settings()` per leggere la chiave Anthropic dal `.env`
- 4 nuovi test unitari per `AnthropicInterface` in `tests/integrations/llm_interfaces/test_anthropic_interface.py`
- Test Claude (test 6) in `dev_support/verify_connections.py`

### Modificato

- Market Analyst migrato da GPT-5.4 (`OpenAiInterface`) a Claude Sonnet 4.6 (`AnthropicInterface`)
- `config/llm_models/market_analyst.yaml` aggiornato: provider `anthropic`, modello `claude-sonnet-4-6`, rimosso `reasoning_effort`
- `src/main.py`: `OpenAiInterface` istanziata 1 sola volta (Decision Maker), aggiunto bootstrap `AnthropicInterface` per Market Analyst
- `tests/test_main.py`: aggiornati tutti i test, aggiunto `claude_api_key` a `_FAKE_SETTINGS`, rinominato `test_main_creates_openai_interface_twice` → `test_main_creates_openai_interface_once`, aggiunto `test_main_creates_anthropic_interface_once`
- Prompt runtime (`config/prompts/`): corretta la gerarchia in tutti e 3 i prompt degli agenti — da "gerarchia operativa" (flusso di lavoro) a "gerarchia di autorità" (Risk Manager al vertice, Execution Trader alla base)
- `docs/hierarchy_and_roles.md`: riscritto completamente con diagramma di autorità, tabella dei livelli e regola fondamentale del potere di veto
- Documentazione aggiornata: README, architecture, config, api_endpoints, repo_structure

---

## 1.1.0 — 2026-03-31

### Aggiunto

- `MemoryManager`: nuovo componente che persiste le decisioni di ogni ciclo su file JSONL in `data/memory/{symbol}.jsonl`
- Il `Decision Maker` riceve ora memoria storica ad ogni ciclo tramite i campi `ia_memory`, `performance_summary` e `recent_performance` di `TradingCycleInput`
- `performance_summary`: calcola automaticamente profitti e perdite confrontando i prezzi di SELL con i BUY precedenti
- 6 nuovi test unitari per `MemoryManager` in `tests/utils/test_memory_manager.py`

---

## 1.0.0 — 2026-03-30

Prima release: MVP completo.

- Sistema multi-agente con 4 ruoli: Market Analyst, Decision Maker, Risk Manager, Execution Trader
- Market Analyst e Decision Maker su GPT-5.4, Risk Manager su Gemini 3.1 Pro, Execution Trader senza LLM
- Client Binance con supporto DEMO e REAL
- Indicatori tecnici: RSI, MACD, EMA, SMA su kline 1h
- Loop operativo ciclico con intervallo configurabile
- Kill switch per bloccare le operazioni
- Retry automatico su risposte LLM non valide
- Logging su console + file rotante + log strutturati JSON per ciclo
- 88 test unitari
- Script di verifica connessioni API
