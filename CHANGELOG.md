<!-- markdownlint-disable -->
# 📋 Changelog

## 1.7.0 — 2026-04-14

### Aggiunto

- Retry automatico con `tenacity` sui 4 metodi di sola lettura di `BinanceClient` (`ping`, `get_account_info`, `get_market_snapshot`, `get_portfolio_state`): backoff esponenziale (2-30s), massimo 3 tentativi. Il retry scatta solo su errori retriabili (`BinanceRequestException`, codici 429/418/5xx). I metodi di scrittura (`place_market_order`, `place_limit_order`, `cancel_order`) restano senza retry per evitare operazioni duplicate
- `AnthropicInterface` aggiunta agli export di `src/integrations/llm_interfaces/__init__.py`
- Campo `quote_currency` in `config/symbols.yaml`: la quote currency ora è un valore esplicito dal config, non più hardcoded. `load_symbol_config` ritorna un `dict` con `symbol` e `quote_currency`; `BinanceClient` riceve `quote_currency` nel costruttore e lo usa in `get_portfolio_state` con `removesuffix` al posto di `replace("USDC", "")`
- 3 nuovi test per il retry Binance e la validazione `quote_currency`

### Modificato

- Retry loop LLM estratto dai 3 agenti in `BaseAgent._call_llm_with_retry`: elimina la duplicazione del blocco retry identico in `market_analyst.py`, `decision_maker.py` e `risk_manager.py`. Il comportamento è invariato (4 tentativi, backoff 4s→8s→16s). Il logger è stato spostato in `BaseAgent.__init__`
- `ping()` in `BinanceClient`: ora ritorna `False` in caso di eccezione invece di propagarla al chiamante

---

## 1.6.1 — 2026-04-14

### Corretto

- `execution_trader.py`: sostituiti i 6 `assert` in `_execute_order` con controlli espliciti che sollevano `ValueError`. Gli `assert` venivano rimossi dal compilatore con `python -O`, rendendo la validazione inaffidabile. I `ValueError` vengono catturati dal `except Exception` in `run()` e restituiscono un `ExecutionReport` con status `FAILED`
- `execution_trader.py`: gestito lo stato parziale in `CANCEL_AND_REPLACE_ORDER` — se `cancel_order` riesce ma `place_limit_order` fallisce, viene loggato un warning e sollevato un `RuntimeError` con messaggio esplicito che compare nel `reason` del report `FAILED` e nelle notifiche Telegram di errore
- `binance_client.py`: sostituito il pattern `if BUY / else` con `if BUY / elif SELL / else raise ValueError` in `place_market_order` e `place_limit_order`. In precedenza qualsiasi valore diverso da `"BUY"` veniva silenziosamente trattato come SELL

### Aggiunto

- 6 nuovi test in `tests/agents/test_execution_trader.py`: BUY senza quantity → `FAILED`, SELL LIMIT senza price → `FAILED`, CANCEL_AND_REPLACE senza order_id → `FAILED`, CANCEL_AND_REPLACE con place fallito → `FAILED` con messaggio "cancelled but replacement failed"
- 2 nuovi test in `tests/integrations/exchange/test_binance_client.py`: `place_market_order` con side non valido → `ValueError`, `place_limit_order` con side non valido → `ValueError`

---

## 1.6.0 — 2026-04-13

### Aggiunto

- Metodo privato `_compute_fifo_trades()` in `memory_manager.py`: calcola le vendite realizzate usando il metodo FIFO (First In, First Out), tracciando una coda di lotti di acquisto e consumandola in ordine cronologico per ogni SELL eseguita. Gestisce vendite parziali e vendite che attraversano più lotti
- Metodo privato `_build_fifo_index()` in `memory_manager.py`: mappa ogni record SELL al suo P&L FIFO per arricchire `get_recent_performance()`

### Modificato

- `get_performance_summary()` in `memory_manager.py`: sostituisce il calcolo approssimativo (BUY più recente -> SELL) con la logica FIFO. Il riassunto ora include P&L percentuale medio e P&L totale in USDC
- `get_recent_performance()` in `memory_manager.py`: i record delle SELL eseguite ora includono `realized_pnl` (USDC) e `pnl_pct` (%) calcolati con metodo FIFO. Il campo `quantity` è stato aggiunto a tutti i record
- Prompt del Decision Maker: aggiornata la descrizione di `performance_summary` e `recent_performance` per riflettere i nuovi campi FIFO
- Test `tests/utils/test_memory_manager.py`: riscritti e ampliati con scenari FIFO (acquisti multipli, vendita parziale, vendita multi-lotto, SELL senza BUY, record invalidi)

---

## 1.5.3 — 2026-04-13

### Modificato

- Aggiunto lo scopo del sistema (generare rendimento sul capitale) nella sezione SCOPO del prompt del Decision Maker
- Aggiunta nota alla sezione "Memoria e performance" del prompt del Decision Maker per chiarire il perché di quei dati, lasciando all'agente l'autonomia su come usarli

---

## 1.5.2 — 2026-04-13

### Modificato

- Rimosso il campo `recent_public_trades` da `MarketDataSnapshot` (`contracts.py`), dalla raccolta dati in `binance_client.py` e dal prompt del Market Analyst: il dato (10 trade pubblici) era rumore inutile su BTC e occupava token nel contesto LLM senza aggiungere valore informativo
- Aumentato il numero di candele per tutti i timeframe in `_fetch_candles` (`binance_client.py`): da 1-2 a valori significativi (12 × 2h, 14 × 4h, 14 × 1d, 8 × 1w, 6 × 1M) per dare al Market Analyst un contesto storico adeguato
- Rinominate le chiavi delle candele da formato verboso (`last_2_candles_2h`, `last_1_candle_1d`, ecc.) a formato semplificato (`candles_2h`, `candles_1d`, ecc.)
- Aggiornato il prompt del Market Analyst per riflettere le nuove chiavi e quantità di candele

---

## 1.5.1 — 2026-04-13

### Aggiunto

- Gestione SIGTERM in `runner.py`: il runner ora intercetta sia `SIGINT` (Ctrl+C) che `SIGTERM` (`docker stop`) tramite signal handler, garantendo l'invio della notifica di stop in qualsiasi scenario di arresto pulito. In precedenza, solo `KeyboardInterrupt` veniva gestito e la notifica di stop non partiva quando il container Docker veniva fermato
- Sezione "Notifiche Telegram" in `docs/observability.md`: documenta le 4 notifiche (avvio, ordine eseguito, errore, stop), con esempio e configurazione
- Test per SIGTERM in `tests/core/test_runner.py`: verifica che la notifica di stop venga inviata anche alla ricezione del segnale SIGTERM

### Modificato

- Testi notifiche Telegram in `runner.py`: tutti i messaggi sono ora in inglese con emoji nel titolo e riga vuota di separazione tra titolo e campi (es. `🚀 Bot STARTED`, `✅ Order EXECUTED`, `⚠️ Cycle ERROR`, `🛑 Bot STOPPED`). In precedenza i testi erano in italiano e senza emoji
- Test notifiche in `tests/core/test_runner.py`: aggiornate le asserzioni per corrispondere ai nuovi testi in inglese

---

## 1.5.0 — 2026-04-13

### Aggiunto

- GitHub Actions CI (`.github/workflows/ci.yml`): workflow che esegue automaticamente tutti i test pytest ad ogni push e pull request. Non richiede secrets perché i test sono unitari con mock. Badge di stato CI aggiunto al README

---

## 1.4.7 — 2026-04-13

### Corretto

- `AnthropicInterface.generate_json()`: aggiunta funzione `_strip_markdown_json()` che pulisce la risposta di Claude prima del parsing JSON. Claude a volte ignora l'istruzione di rispondere con JSON puro e wrappa la risposta in un code block markdown (` ```json...``` `), causando un `json.JSONDecodeError` non recuperabile dal retry. La funzione estrae il JSON puro rimuovendo il wrapping markdown o, come fallback, estraendo il sottostringa dal primo `{` all'ultimo `}`. Questo risolve un errore ricorrente in produzione confermato dai log della VM

### Aggiunto

- 7 nuovi test in `tests/integrations/llm_interfaces/test_anthropic_interface.py`: 4 test unitari per `_strip_markdown_json` (wrapping con tag `json`, wrapping senza tag, testo extra prima del JSON, JSON puro invariato) e 3 test di integrazione per `generate_json` (risposta con ` ```json...``` `, risposta con ` ```...``` `, risposta con testo prima del JSON)

---

## 1.4.6 — 2026-04-12

### Aggiunto

- Diagnostica risposte vuote LLM: le 3 interfacce (`openai_interface.py`, `anthropic_interface.py`, `gemini_interface.py`) ora loggano a livello WARNING le metadata del provider (`finish_reason`, `usage`/`usage_metadata`, `stop_reason`) quando la risposta è vuota, prima di lanciare il `RuntimeError`. In precedenza il motivo della risposta vuota era invisibile nei log
- Backoff esponenziale nei retry degli agenti LLM: aggiunta una pausa crescente (4s → 8s → 16s) tra i tentativi in `market_analyst.py`, `decision_maker.py`, `risk_manager.py`. In precedenza i retry partivano immediatamente uno dopo l'altro, senza dare tempo al provider di recuperare
- 6 nuovi test: 3 per le interfacce LLM (verifica log diagnostico su risposta vuota) e 3 per gli agenti (verifica valori di backoff `time.sleep`)

### Modificato

- Retry nei 3 agenti LLM portato da 3 a 4 tentativi (`max_attempts = 4`)

---

## 1.4.5 — 2026-04-12

### Modificato

- Python aggiornato da 3.12 a 3.14 (ambiente locale e `Dockerfile` per il deploy)

---

## 1.4.4 — 2026-04-10

### Corretto

- Le 3 interfacce LLM (`anthropic_interface.py`, `openai_interface.py`, `gemini_interface.py`) ora sollevano `RuntimeError` quando il provider risponde con testo vuoto o con un JSON vuoto `{}`. In precedenza il fallback `or "{}"` mascherava silenziosamente queste risposte, che passavano l'interfaccia senza errori e venivano rilevate solo dall'agente, dove il retry aveva meno tentativi. Con il fix, il `RuntimeError` viene lanciato direttamente nell'interfaccia e il retry dell'agente scatta immediatamente
- Il messaggio di WARNING del retry nei 3 agenti LLM ora include di nuovo la risposta raw del modello (`| Risposta: ...`), rimossa per errore nel refactoring v1.4.3

### Modificato

- Retry nei 3 agenti LLM portato da 2 a 3 tentativi (`max_attempts = 3`)

### Aggiunto

- 6 nuovi test per le interfacce LLM (2 per interfaccia): risposta vuota e JSON vuoto `{}` sollevano `RuntimeError`
- 6 nuovi test per gli agenti (2 per agente): verifica che il retry raggiunga esattamente 3 tentativi e che il WARNING includa la risposta raw

---

## 1.4.3 — 2026-04-10

### Corretto

- Retry nei 3 agenti LLM (`market_analyst.py`, `decision_maker.py`, `risk_manager.py`): la chiamata a `generate_json()` era fuori dal blocco `try/except`, quindi un `RuntimeError` lanciato dall'interfaccia (es. JSON non decodificabile) bypassava il retry e faceva fallire il ciclo al primo tentativo. Ora `generate_json()` è dentro il try e `RuntimeError` è tra le eccezioni catturate
- Il messaggio di WARNING del retry non includeva più la risposta raw (rimossa per errore dal refactoring precedente) — non era un problema bloccante ma riduceva la leggibilità dei log

### Aggiunto

- Le 3 interfacce LLM (`anthropic_interface.py`, `openai_interface.py`, `gemini_interface.py`) loggano ora la risposta raw a livello WARNING quando il `json.loads` fallisce, rendendo sempre visibile cosa ha risposto il modello anche in caso di errore
- 3 nuovi test di integrazione (uno per interfaccia): verifica che il log WARNING con la risposta raw venga emesso su JSON non valido
- 3 nuovi test agenti (uno per agente): verifica che `RuntimeError` da `generate_json` attivi correttamente il retry

---

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
