<!-- markdownlint-disable -->
# 📋 Changelog

## 1.13.3 — 2026-04-27

### Corretto

- `src/utils/indicators.py`: rimosso `import numpy as np`, che era rimasto inutilizzato. Gli indicatori del file usano solo `pandas`, quindi l'import extra era rumore inutile.
- `tests/test_main.py`: rimosso `call` dagli import di `unittest.mock`, dato che il test non lo usa in nessun punto.
- `src/agents/base_agent.py`, `src/agents/market_analyst.py`, `src/agents/risk_manager.py`, `src/agents/performance_reviewer.py`: semplificata `_ensure_list_of_str()` eliminando il parametro `field_name`, che non veniva mai usato, e aggiornati tutti i chiamanti.
- `src/agents/market_analyst.py`, `src/agents/decision_maker.py`, `src/agents/risk_manager.py`, `src/agents/performance_reviewer.py`: sostituiti i guard `assert self.prompt_path is not None` con controlli espliciti che sollevano `RuntimeError`. In questo modo la validazione resta attiva anche con `python -O`, dove gli assert vengono rimossi dal runtime.
- `tests/agents/test_agent_interfaces.py`: aggiornati i test per la nuova firma di `_ensure_list_of_str()` e aggiunta una regressione che verifica l'errore esplicito quando un agente non ha un prompt configurato.

---

## 1.13.2 — 2026-04-27

### Corretto

- `src/integrations/exchange/binance_client.py`: allineate le chiavi RSI restituite dagli indicatori da `rsi_14` / `rsi_14_prev` a `rsi` / `rsi_prev`. Questo ripristina il funzionamento del pre-check di cycle skip, che leggeva gia' `rsi` e quindi non riusciva mai a confrontare correttamente la variazione dell'indicatore.
- `config/prompts/market_analyst.md`: aggiornata la documentazione del payload in input per usare `rsi` / `rsi_prev`, coerentemente con le chiavi realmente passate dal runner al prompt.
- `tests/integrations/exchange/test_binance_client.py`: aggiornata la regressione sul market snapshot per verificare le chiavi RSI corrette ed evitare il ritorno accidentale dei nomi legacy.
- `tests/core/test_runner.py`: corretta l'asserzione sulla notifica ordine non eseguito da `ESEGUITO` a `EXECUTED`, cosi' il test verifica davvero il testo reale inviato dal runner.

---

## 1.13.1 — 2026-04-27

### Aggiunto

- `.github/dependabot.yml`: configurazione Dependabot per aggiornamenti automatici settimanali delle dipendenze Python. Tutti gli aggiornamenti vengono raggruppati in un'unica PR settimanale (lunedì 09:00, `Europe/Rome`), che attiva automaticamente la CI pytest prima del merge.

---

## 1.13.0 — 2026-04-22

### Aggiunto

- **Cycle skip deterministico**: pre-check opzionale che salta un ciclo operativo quando il contesto di mercato e' sostanzialmente invariato rispetto al precedente, evitando di chiamare Market Analyst, Decision Maker (Opus con thinking) e Risk Manager quando non serve. Motivazione: dai log del 22/04 risultavano 5 HOLD consecutivi in ~6 ore con delta indicatori minimi e zero ordini eseguiti — ogni ciclo consumava comunque la catena LLM completa.
- `config/cycle_skip.yaml`: nuovo file con `enabled`, `max_consecutive_skips` e `thresholds` (`price_delta_pct`, `rsi_delta`, `macd_sign_must_match`, `require_no_order_events`, `require_previous_action_hold`).
- `src/core/contracts.py`: nuove dataclass `CycleSkipConfig` e `CycleContextSnapshot`.
- `src/utils/config.py`: `load_cycle_skip_config()` con fallback safe (`enabled=false`) se il file manca.
- `src/utils/cycle_skip.py`: funzione pura `should_skip_cycle()` che decide in modo deterministico se saltare il ciclo corrente, e helper `extract_open_order_ids()`.
- `src/utils/event_logger.py`: nuovo metodo `log_skipped_cycle()` che scrive un record JSON distinto con `cycle_type: "skipped"` (senza payload agenti).
- `src/core/runner.py`: integrato il pre-check prima della catena decisionale. Lo snapshot del contesto precedente vive solo in RAM (primo ciclo post-restart sempre full). Counter `_consecutive_skips` per garantire una rivalutazione dopo N skip.

### Documentazione

- `README.md`: bump `1.12.0` → `1.13.0`.
- `docs/config.md`: nuova sezione "Cycle skip" con spiegazione dei campi.
- `docs/decision_logic.md`: aggiunta la menzione del pre-check deterministico prima della catena di agenti.
- `docs/repo_structure.md`: aggiunti `config/cycle_skip.yaml`, `src/utils/cycle_skip.py` e `tests/utils/test_cycle_skip.py`.

### Test

- `tests/utils/test_cycle_skip.py`: nuovo file, copertura di `should_skip_cycle` su tutti i casi limite (disabilitato, primo ciclo, counter al massimo, ogni soglia violata, contesto invariato).
- `tests/utils/test_config.py`: aggiunti test per `load_cycle_skip_config` (valori corretti, file mancante, campi mancanti).
- `tests/utils/test_event_logger.py`: aggiunto test per `log_skipped_cycle`.
- `tests/core/test_runner.py`: aggiunti test di integrazione (skip attivo + contesto invariato → workflow non chiamato; skip disabilitato → workflow chiamato; primo ciclo mai saltato).

## 1.12.0 — 2026-04-22

### Modificato

- `config/trading.yaml`: semplificato il mandato. Rimossi i campi `objective`, `min_monthly_return_pct` e `min_trades_per_week`. Motivazione: i target numerici (rendimento mensile minimo e trade minimi settimanali) generavano comportamento coercitivo nel Decision Maker, che finiva per forzare trade anche in assenza di setup (es. evento del 21/04 motivato esplicitamente come "trade settimanale richiesto dal mandato"). L'`objective` testuale invece non è un dato variabile del ciclo: fa parte dell'identità del DM e va nel prompt, non nel config. Restano nel mandato solo i vincoli di rischio e il contesto strategico: `max_drawdown_pct`, `horizon`, `max_position_pct`.
- `src/core/contracts.py`: `InvestmentMandate` ridotto a 3 campi (`max_drawdown_pct`, `horizon`, `max_position_pct`).
- `src/utils/config.py`: `load_mandate` allineato alla nuova struttura (validazione solo sui 3 campi rimasti).
- `src/utils/performance_stats.py`: il report markdown non stampa più Obiettivo / Rendimento mensile minimo / Trade minimi per settimana.
- `config/prompts/decision_maker.md`: integrata "Generare rendimento sul capitale" nella sezione `SCOPO`. Rimossi i riferimenti ai 3 campi eliminati dalla sezione `Mandato operativo`. Riformulato il principio anti-HOLD-bias in chiave qualitativa: il DM deve valutare il setup di mercato, non conteggiare trade o rendimenti rispetto a target numerici.
- `config/prompts/performance_reviewer.md`: verdetto `ALIGNED` / `DRIFTING` / `MISALIGNED` ridefinito in chiave qualitativa. Non si valuta più rispetto a `min_trades_per_week` o `min_monthly_return_pct`, ma rispetto alla coerenza delle decisioni con il contesto di mercato e i vincoli di rischio.

### Documentazione

- `README.md`: bump `1.11.1` → `1.12.0`.
- `docs/config.md`: snippet YAML e tabella dei campi del mandato aggiornati. Aggiunta nota sul razionale della rimozione dei target numerici.
- `docs/decision_logic.md`: sezione Decision Maker riallineata alla nuova forma del mandato.

### Test

- `tests/core/test_contracts.py`, `tests/utils/test_config.py`, `tests/agents/test_decision_maker.py`, `tests/agents/test_performance_reviewer.py`, `tests/utils/test_performance_stats.py`, `tests/core/test_workflow.py`, `tests/core/test_runner.py`: fixture del mandato aggiornate ai 3 campi rimanenti; asserzioni sui campi rimossi eliminate.

## 1.11.1 — 2026-04-21

### Corretto

- `AnthropicInterface._build_kwargs`: corretto il formato della richiesta verso l'API Anthropic per Opus 4.7 con adaptive thinking. Il parametro `effort` non va più annidato dentro `thinking` (che causava errore 400 `thinking.adaptive.effort: Extra inputs are not permitted`), ma viene ora inviato nel campo separato `output_config`, come richiesto dalla documentazione ufficiale Anthropic. Quindi: `thinking={"type": "adaptive"}` e `output_config={"effort": "high"}` come kwarg distinti.
- Aggiornato il test `test_thinking_effort_enables_thinking_and_removes_temperature` che verificava il formato sbagliato e aggiunto nuovo test di regressione `test_without_thinking_effort_does_not_send_output_config` per garantire che `output_config` non venga inviato quando `thinking_effort` è `None` (Performance Reviewer su Sonnet 4.6).
- `AnthropicInterface.generate_text`: ora gestisce in modo robusto la risposta vuota (stessa logica già presente in `generate_json`): logga un warning con `stop_reason` e `usage`, poi solleva `RuntimeError`. Prima ritornava silenziosamente una stringa vuota, mascherando potenziali problemi di budget token esaurito durante il thinking.
- Aggiunto test `test_generate_text_empty_response_logs_and_raises` per la nuova gestione degli edge case in `generate_text`.
- `_extract_text`: docstring aggiornato per riflettere il comportamento attuale di Opus 4.7, dove i blocchi `thinking` arrivano vuoti di default (a meno di `display: "summarized"`).

## 1.11.0 — 2026-04-21

### Modificato

- Riassegnazione dei modelli LLM degli agenti:
  - **Decision Maker**: da `GPT-5.4` (OpenAI) a `Claude Opus 4.7` (Anthropic) con adaptive thinking (`thinking_effort: high`). Motivazione: ragionamento strutturato superiore per decisioni ambigue e gestione dinamica della posizione.
  - **Market Analyst**: da `Claude Sonnet 4.6` (Anthropic) a `GPT-5.4` (OpenAI) senza reasoning. Motivazione: analisi tecnica deterministica, no bisogno di thinking, budget token liberato.
  - `Risk Manager` (Gemini 3.1 Pro) e `Performance Reviewer` (Claude Sonnet 4.6) restano invariati.
- `config/llm_models/decision_maker.yaml`: provider `anthropic`, modello `claude-opus-4-7`, nuovo parametro `thinking_effort: high`, `max_tokens: 16384` (budget condiviso tra thinking e output). `temperature` rimossa (Opus 4.7 non la accetta con thinking).
- `config/llm_models/market_analyst.yaml`: provider `openai`, modello `gpt-5.4`, `temperature: 0.2`, `max_tokens: 4096`. Nessun `reasoning_effort`.

### Aggiunto

- `AnthropicInterface`: nuovo parametro opzionale `thinking_effort: str | None = None` e helper interno `_build_kwargs`/`_extract_text`:
  - Se `thinking_effort` è valorizzato (es. `"high"`): passa `thinking: {"type": "adaptive", "effort": ...}`, NON passa `temperature` (rifiutata da Opus 4.7 con thinking) e estrae solo i blocchi `text` dalla risposta (scartando quelli `thinking`).
  - Se `thinking_effort` è `None` (default): comportamento identico al precedente (passa `temperature`, concatena i blocchi `text`). Retrocompatibilità totale con Sonnet 4.6 usato dal `Performance Reviewer`.
- 4 nuovi test in `tests/integrations/llm_interfaces/test_anthropic_interface.py`: `thinking_effort` abilita `thinking` e rimuove `temperature`; regressione senza `thinking_effort`; estrazione text ignora blocchi `thinking`; concatenazione di più blocchi `text`.

### Documentazione

- README.md: bump `1.10.0` → `1.11.0`, tabella agenti aggiornata con `Claude Opus 4.7 (thinking)` per DM e `GPT-5.4` per MA, sezione "API integrate" riallineata.
- `docs/config.md`: snippet YAML di `decision_maker.yaml` e `market_analyst.yaml` aggiornati; documentato il parametro `thinking_effort`.
- `docs/architecture.md`: modelli degli agenti aggiornati nella descrizione dei ruoli.
- `docs/decision_logic.md`: menzione del passaggio del DM a Opus 4.7 con adaptive thinking.

---

## 1.10.0 — 2026-04-20

### Modificato

- `config/prompts/decision_maker.md`: nuova sezione "Gestione dinamica della posizione" che abilita **scaling in** (ingresso in 2-3 tranche con `MARKET BUY` + `LIMIT BUY` successivi) e **take profit parziali** (`LIMIT SELL` sopra il prezzo corrente con `quantity` frazionale). I riferimenti numerici (30-50% per tranche, +10/+15% per TP) sono indicativi di buona pratica, non vincoli rigidi: il DM resta libero di adattarli al contesto
- `config/prompts/decision_maker.md`: aggiunta regola esplicita che chiarisce come le `quantity` possano essere frazionali rispetto al portafoglio (non più solo "tutto dentro / tutto fuori")
- `config/prompts/decision_maker.md`: aggiunto divieto esplicito di usare `LIMIT SELL` sotto il prezzo corrente come finto stop loss — su Binance spot un limit sotto mercato viene eseguito immediatamente. Finché non saranno introdotti i tipi di ordine avanzati, il DM deve usare `MARKET SELL` (totale o parziale) per uscire in perdita

### Aggiunto

- 2 nuovi esempi JSON nello schema risposta del prompt DM: "Scaling in — prima tranche" (`BUY MARKET` con quantity parziale) e "Take profit parziale" (`SELL LIMIT` sopra mercato con quantity parziale)
- 2 nuovi test dimostrativi in `tests/agents/test_decision_maker.py`: `test_parse_buy_market_scaling_in_first_tranche` e `test_parse_sell_limit_partial_take_profit`. Il parser supportava già quantity frazionali: questi test esplicitano l'intento della Fase 3 e fanno da regressione

### Configurazione

- `config/llm_models/market_analyst.yaml`, `risk_manager.yaml`, `performance_reviewer.yaml`: `max_tokens` alzato da `2048` a `4096`. Per Gemini 3.1 Pro i thinking tokens consumano parte del budget output (come GPT-5.4): il margine precedente era troppo stretto per proposte complesse. Per Claude il thinking è separato da `max_tokens`, ma il valore è stato alzato comunque per uniformità

### Documentazione

- `docs/decision_logic.md`: sezione Decision Maker aggiornata con le nuove capacità (scaling in, TP parziali, quantity frazionali) e con la nota che lo stop loss proattivo è rimandato a una fase futura
- `docs/config.md`: aggiornati gli snippet YAML dei modelli LLM con i nuovi valori di `max_tokens` e aggiunto lo snippet del Performance Reviewer
- `docs/deploy.md`: aggiunta guida "Scaricare log ed eventi in locale" nella sezione comandi utili, con gestione del caso utenti SSH diversi

---

## 1.9.0 — 2026-04-20

### Aggiunto

- Nuovo agente `Performance Reviewer` (5° agente) in `src/agents/performance_reviewer.py`. Ruolo consultivo, fuori dalla catena decisionale: analizza i cicli degli ultimi 7 giorni e produce un giudizio giornaliero (summary, aderenza al mandato `ALIGNED`/`DRIFTING`/`MISALIGNED`, 1-3 suggerimenti concreti) letto dal Decision Maker nei cicli successivi. Usa Claude Sonnet 4.6 riciclando `AnthropicInterface` (zero nuovo codice di integrazione)
- Nuovo prompt `config/prompts/performance_reviewer.md` e nuova config `config/llm_models/performance_reviewer.yaml`
- Nuova funzione `load_recent_events` in `src/utils/event_log_reader.py` che legge gli eventi JSONL degli ultimi N giorni filtrandoli per simbolo
- Nuova funzione `build_performance_stats` in `src/utils/performance_stats.py`: calcolo deterministico (zero LLM) di statistiche operative (HOLD ratio, segnali forti ignorati, SELL falliti, P&L FIFO, giorni senza trade eseguito, ecc.)
- Nuovo helper `write_performance_report` che serializza il report in markdown e lo salva in `data/performance_reports/YYYY-MM-DD.md`
- Nuovo dataclass `PerformanceStats`, `PerformanceReview`, `PerformanceReviewerInput` e enum `MandateAdherence` in `src/core/contracts.py`
- `TradingCycleInput` e `DecisionMakerInput` estesi con `latest_performance_review: str` (default vuoto: se il report di oggi non c'è, il DM riceve stringa vuota e non si altera)
- Trigger giornaliero nel runner: nuovi metodi `_maybe_run_performance_review` (genera il report una volta al giorno, errori non bloccano il ciclo) e `_load_latest_performance_review` (legge il file più recente)
- 13 nuovi test: `tests/utils/test_event_log_reader.py` (4), `tests/utils/test_performance_stats.py` (6 + 1 writer), `tests/agents/test_performance_reviewer.py` (7), più 5 test aggiunti a `tests/core/test_runner.py` per il trigger giornaliero

### Modificato

- `config/prompts/decision_maker.md`: nuova sottosezione "Performance review" che descrive il campo `latest_performance_review` e impone al DM di leggerlo e incorporarlo nelle decisioni quando il Reviewer segnala `DRIFTING` o `MISALIGNED`
- `src/core/runner.py`: costruttore esteso con `performance_reviewer` e `performance_reports_dir`; `_run_single_cycle` chiama `_maybe_run_performance_review` a inizio ciclo; `_build_cycle_input` popola `latest_performance_review` col contenuto del file più recente
- `src/core/workflow.py`: `latest_performance_review` viene propagato dal `TradingCycleInput` al `DecisionMakerInput`
- `src/agents/decision_maker.py`: `latest_performance_review` viene incluso nel payload passato al LLM
- `src/main.py`: caricamento di `performance_reviewer.yaml`, istanziazione di `AnthropicInterface` e `PerformanceReviewerAgent`, passaggio al runner

### Documentazione

- README.md: bump versione `1.8.0` → `1.9.0`; tabella agenti aggiornata con `Performance Reviewer`; sezione "Come funziona" riscritta per includere il trigger giornaliero
- `docs/decision_logic.md`, `docs/architecture.md`, `docs/hierarchy_and_roles.md`, `docs/observability.md`, `docs/repo_structure.md`: aggiornati per descrivere il Performance Reviewer, il nuovo campo `latest_performance_review`, la nuova cartella `data/performance_reports/` e i nuovi file nella repo

---

## 1.8.0 — 2026-04-20

### Aggiunto

- Nuova sezione `mandate` in `config/trading.yaml` che definisce l'investment mandate del sistema (obiettivo, rendimento mensile minimo, drawdown massimo, orizzonte, posizione massima, trade minimi per settimana). Il mandato funge da "bussola" operativa per il Decision Maker
- Nuovo dataclass `InvestmentMandate` in `src/core/contracts.py` che tipizza i campi del mandato
- Nuova funzione `load_mandate(trading_config)` in `src/utils/config.py` che legge e valida la sezione `mandate`: se manca o ha campi incompleti, il runner fallisce in fase di boot con un `ValueError` esplicito
- 4 nuovi test: `test_investment_mandate_stores_all_fields` in `tests/core/test_contracts.py` e 3 test per `load_mandate` in `tests/utils/test_config.py` (happy path, sezione mancante, campo mancante)

### Modificato

- `config/prompts/decision_maker.md`: rimossa la regola "Se il segnale non è chiaro... scegli HOLD" che generava un bias eccessivo verso l'inazione. Sostituita con un'istruzione che invita a valutare il mandato nell'ambiguità e ribadisce che `HOLD` resta legittimo solo quando il mercato è fermo o i rischi sono concreti. Aggiunta una nuova sezione "Mandato operativo" che descrive i 6 campi del mandate. Riscritta la sezione "Memoria e performance" per rendere obbligatorio l'uso di `ia_memory`, `performance_summary` e `recent_performance` prima di decidere
- `src/core/contracts.py`: `DecisionMakerInput` e `TradingCycleInput` estesi con un campo obbligatorio `mandate: InvestmentMandate`
- `src/core/runner.py`: il mandate viene caricato all'avvio tramite `load_mandate` e propagato a ogni ciclo dentro `TradingCycleInput`
- `src/core/workflow.py`: il mandate viene passato dal `TradingCycleInput` al `DecisionMakerInput`
- `src/agents/decision_maker.py`: il mandate viene incluso nel payload passato al LLM

### Documentazione

- `docs/config.md`: sezione `config/trading.yaml` aggiornata con la descrizione di tutti i campi del mandate e del flusso di caricamento
- `docs/decision_logic.md`: sezione Decision Maker riscritta per spiegare come il mandate guida il ragionamento e come memoria/performance vengono ora consultate prima di ogni decisione

---

## 1.7.4 — 2026-04-20

### Corretto

- `binance_client.py`: `place_market_order` e `place_limit_order` ora leggono i filtri del simbolo da `exchangeInfo` (con cache in memoria) e troncano `quantity` a `stepSize` e `price` a `tickSize` prima di inviare l'ordine. Vengono inoltre validati `minQty` e `minNotional`: se la quantity dopo il rounding non rispetta questi vincoli, viene sollevato un `ValueError` con messaggio chiaro. Questo risolve i fallimenti ricorrenti `Filter failure: LOT_SIZE` che impedivano l'esecuzione dei SELL proposti dal Decision Maker. I calcoli usano `decimal.Decimal` per evitare imprecisioni floating-point
- `config/llm_models/decision_maker.yaml`: `max_tokens` alzato da `2048` a `8192`. Con `reasoning_effort: high` il budget precedente veniva saturato dai reasoning tokens interni, producendo risposte vuote (`finish_reason: length`) e cicli falliti. Il nuovo limite lascia ampio margine sia al reasoning sia all'output JSON

### Aggiunto

- 5 nuovi test in `tests/integrations/exchange/test_binance_client.py`: rounding di `quantity` a `stepSize`, rounding di `price` a `tickSize`, rifiuto sotto `minQty`, rifiuto sotto `minNotional`, cache dei filtri (una sola chiamata `get_symbol_info` per simbolo)

### Manutenzione

- `requirements.txt`: pytest aggiornato da `9.0.2` a `9.0.3` (bump Dependabot).

---

## 1.7.3 — 2026-04-16

### Corretto

- `anthropic_interface.py`: `InternalServerError` aggiunto a `_RETRYABLE_ERRORS` — gli errori 500/529 di Anthropic ora attivano il retry automatico di tenacity (backoff esponenziale, max 3 tentativi) invece di essere propagati direttamente al retry di parsing in `base_agent`
- `openai_interface.py`: stessa fix applicata a OpenAI — `InternalServerError` aggiunto a `_RETRYABLE_ERRORS`

### Aggiunto

- 1 nuovo test in `tests/integrations/llm_interfaces/test_anthropic_interface.py` per il retry su `InternalServerError`
- 1 nuovo test in `tests/integrations/llm_interfaces/test_openai_interface.py` per il retry su `InternalServerError`

### Documentazione

- `docs/decision_logic.md`: sezione "Normalizzazione e retry su errori LLM" riscritta per documentare esplicitamente i due livelli di retry (tenacity al livello API e `_call_llm_with_retry` al livello agente) con l'elenco degli errori riprovabili per ogni interfaccia

---

## 1.7.2 — 2026-04-14

### Corretto

- `base_agent.py`: accenti mancanti nei messaggi di errore di `unwrap_llm_response` (`"e"` → `"è"`)

### Aggiunto

- `telegram_notifier.py`: funzione `escape_html(text)` — escapa caratteri speciali HTML (`<`, `>`, `&`) per le notifiche Telegram. Usata in `runner.py` per sanitizzare `str(exc)` nelle notifiche di errore del ciclo
- 1 nuovo test per `escape_html` in `tests/utils/test_telegram_notifier.py`

### Modificato

- `config.py`: logica di caricamento YAML duplicata tra `load_trading_config`, `load_symbol_config` e `load_llm_model_config` estratta nell'helper privato `_load_yaml` — i 3 loader rimangono invariati nel comportamento esterno

---

## 1.7.1 — 2026-04-14

### Corretto

- `base_agent.py`: `TypeError` aggiunto alla tupla di eccezioni catturate in `_call_llm_with_retry` — gestisce il caso in cui il JSON del LLM contenga tipi inattesi (es. `float(None)`)
- `base_agent.py`: `prompt_path` ancorato alla root del progetto con `Path(__file__).resolve()` invece di `Path("config")` relativo alla cwd — il path ora funziona correttamente indipendentemente da dove viene lanciato il processo
- `base_agent.py`: `prompt_name` reso opzionale (`default=""`); `prompt_path` ritorna `None` se non configurato. `ExecutionTraderAgent` (che non usa LLM) non passa più `prompt_name` al super
- `event_logger.py` e `memory_manager.py`: `datetime.now()` sostituito con `datetime.now(timezone.utc)` — i timestamp sono ora timezone-aware in UTC
- `runner.py`: `time.sleep()` sostituito con `threading.Event.wait()` — lo sleep del runner è ora interrompibile immediatamente da SIGTERM/SIGINT senza aspettare il timeout completo

### Aggiunto

- `base_agent.py`: funzione `_ensure_list_of_str(value, field_name)` — normalizza campi lista dalla risposta LLM in `list[str]`, gestendo lista, stringa singola e tipi inattesi. Usata nei parser di `market_analyst.py` e `risk_manager.py` per `key_factors`, `risk_notes`, `checks`, `required_changes`
- 5 nuovi test per `_ensure_list_of_str` e `prompt_path` in `tests/agents/test_agent_interfaces.py`

### Modificato

- `memory_manager.py`: logica FIFO duplicata tra `_compute_fifo_trades` e `_build_fifo_index` estratta nel metodo privato `_walk_fifo` — le due funzioni pubbliche diventano semplici trasformazioni del risultato condiviso

---

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
