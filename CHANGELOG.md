<!-- markdownlint-disable -->
# 📋 Changelog

## 1.25.2 — 2026-06-08

### Refactoring

- `src/core/position_manager.py`: nuova classe `PositionManager` estratta da `runner.py`. Raccoglie le tre responsabilità legate alla posizione aperta: calcolo P&L non realizzato via FIFO (`augment_portfolio_with_open_position`), breakeven automatico dell'OCO (`maybe_apply_breakeven`) e flag di revisione periodica OCO (`is_oco_review_required`). La costante `_POSITION_QTY_TOLERANCE` si sposta in questo modulo.
- `src/core/runner.py`: rimossi i tre metodi estratti e `_POSITION_QTY_TOLERANCE`; rimossi gli attributi `_breakeven_trigger_pct` e `_oco_review_interval_hours` dal runner; istanziato `PositionManager` in `__init__` con i valori letti da `_trading_config`; aggiornate le chiamate in `_run_single_cycle` e `_build_cycle_input`.
- `tests/core/test_position_manager.py`: nuovo file con i 17 test spostati da `test_runner.py` (5 augment portfolio, 8 breakeven, 4 OCO review); i test usano `_make_position_manager(...)` e chiamano i metodi direttamente senza passare per il runner.
- `tests/core/test_runner.py`: rimossi i 17 test spostati; adattato `test_build_cycle_input_sets_oco_review_required_true` per accedere a `runner._position_manager._oco_review_interval_hours`; rimosso import inutilizzato `ExecutionReport`.

## 1.25.1 — 2026-06-08

### Corretto

- `src/agents/execution_trader.py`: il guardrail del cap percentuale (`max_position_pct`) usava `portfolio.usdc_balance` (USDC **liberi**) come parte del denominatore, mescolandolo con `usdc_value` (controvalore **totale** delle monete). Ora usa `portfolio.usdc_balance_total` (USDC liberi + bloccati), così il denominatore è coerentemente il valore totale del portafoglio. Il bug poteva solo bloccare erroneamente ordini legittimi quando c'erano USDC bloccati in ordini aperti (direzione conservativa, mai pericolosa).

### Test

- `tests/agents/test_execution_trader.py`: aggiornata la docstring di `test_guardrail_portfolio_pct_uses_total_portfolio_value`; nuovo test `test_guardrail_portfolio_pct_uses_total_usdc_not_free` — con 50 USDC liberi + 950 bloccati (1000 totali) e 1000 di monete, un SELL da 800 USDC (40% del totale) passa il limite del 70%, mentre col vecchio denominatore (1050) sarebbe stato 76% e bloccato.

### Documentazione

- `docs/config.md`: descrizione di `mandate.max_position_pct` precisata con il denominatore usato dal guardrail (valore totale del portafoglio).

## 1.25.0 — 2026-06-08

### Aggiunto

- `src/core/contracts.py`: nuovo campo `min_order_usdc: float = 0.0` in `ExecutionInput`. Default `0.0` = guardrail disattivato (retrocompatibile con chi non lo imposta).
- `src/agents/execution_trader.py`: guardrail deterministico in `_validate_guardrails` — se `min_order_usdc > 0` e `notional < min_order_usdc`, restituisce `NOT_EXECUTED` con reason tracciata. Il controllo avviene prima del cap massimo, a specchio di `max_order_notional_usdc`.

### Modificato

- `src/core/workflow.py`: `ExecutionInput` ora riceve `min_order_usdc=cycle_input.constraints.min_order_usdc`.

### Test

- `tests/agents/test_execution_trader.py`: helper `_make_input` aggiornato con parametro `min_order_usdc: float = 0.0`. Nuovi test: `test_guardrail_min_order_blocks_order_below_minimum` (notional 5 USDC < minimo 10 USDC → `NOT_EXECUTED`) e `test_guardrail_min_order_passes_order_above_minimum` (notional 50 USDC > minimo 10 USDC → `EXECUTED`).
- `tests/core/test_workflow.py`: nuovo test `test_workflow_passes_min_order_usdc_to_execution_input` — verifica che `constraints.min_order_usdc` arrivi correttamente a `ExecutionInput`.

### Documentazione

- `docs/config.md`: descrizione di `min_order_usdc` aggiornata per indicare il guardrail deterministico nell'`ExecutionTraderAgent` (a specchio di `max_order_notional_usdc`).
- `docs/decision_logic.md`: sezione "Execution Trader" — aggiunto riepilogo dei guardrail deterministici con menzione esplicita del minimo notional.

## 1.24.3 — 2026-06-08

### Corretto

- `src/core/runner.py`: `_augment_portfolio_with_open_position` calcolava `unrealized_pnl_usdc` moltiplicando `(price - avg_entry)` per `portfolio_qty_total` (saldo totale exchange). Ora usa `open_qty` (quantità tracciata dai lotti FIFO aperti), che è la quantità a cui `avg_entry_price` fa effettivamente riferimento. Le monete non tracciate dalla memoria del bot hanno costo di carico ignoto e non vengono incluse nel calcolo. `unrealized_pnl_pct` era già corretto (dipende solo da prezzo e `avg_entry`).
- `src/core/runner.py`: aggiunto WARNING diagnostico quando `open_qty` e `qty_total` divergono di più dell'1% (`_POSITION_QTY_TOLERANCE`), segnale che la memoria FIFO e il saldo dell'exchange sono disallineati.

### Test

- `tests/core/test_runner.py`: nuovo test `test_augment_portfolio_pnl_usdc_uses_open_qty_not_qty_total` — con `open_qty=0.005` e `qty_total=0.010`, verifica che `unrealized_pnl_usdc` sia calcolato su `open_qty` (il test falliva con il codice precedente).
- `tests/core/test_runner.py`: nuovo test `test_augment_portfolio_logs_warning_on_qty_divergence` — verifica che con divergenza >1% venga emesso un WARNING via `caplog`.

### Documentazione

- `docs/decision_logic.md`: precisato che `unrealized_pnl_usdc` usa la quantità FIFO tracciata (`open_qty`), non il saldo totale dell'exchange.
- `docs/architecture.md`: aggiornate le descrizioni di `PortfolioState` e `compute_open_position` per riflettere il calcolo corretto e il WARNING di divergenza.

## 1.24.2 — 2026-06-08

### Modificato

- `src/utils/memory_manager.py`: introdotta cache per-ciclo. `__init__` inizializza `_records_cache: dict[str, list[dict]]` e `_fifo_cache: dict[str, tuple[list[dict], deque]]`. `_read_all` serve dalla cache se presente, altrimenti legge da disco e salva. `_read_last_n` reimplementato come slice su `_read_all` (stessa semantica, zero I/O aggiuntivo). `_walk_fifo` serve dalla cache se presente, altrimenti calcola e salva. `save_cycle` invalida entrambe le cache per il simbolo scritto dopo aver appeso la riga. Riduce le letture da disco e i ricalcoli FIFO da ~5-6 a 1 per ciclo, senza alcun cambio di comportamento osservabile e senza modifiche all'API pubblica.

### Test

- `tests/utils/test_memory_manager.py`: due nuovi test — `test_cache_serves_stale_data_until_save_cycle` (verifica che la cache mantenga i dati vecchi se il file viene modificato bypassando `save_cycle`, e che torni fresca dopo la chiamata a `save_cycle`) e `test_cache_invalidated_separately_per_symbol` (verifica che l'invalidazione sia isolata per simbolo).

### Documentazione

- `docs/architecture.md`: aggiunta sezione "Cache per-ciclo" nella sezione "Memoria operativa" con descrizione del meccanismo e del beneficio.
- `docs/repo_structure.md`: descrizione di `memory_manager.py` aggiornata con nota sulla cache.

## 1.24.1 — 2026-06-08

### Modificato

- `src/integrations/llm_interfaces/gemini_interface.py`: `temperature` resa opzionale (`float | None = None`). Aggiunto metodo `_config_kwargs` che costruisce i kwargs di `GenerateContentConfig` in modo condizionale: `temperature` viene inclusa solo se valorizzata. Allineamento alla raccomandazione ufficiale Google per Gemini 3.x (default `1.0`, non impostare valori bassi su modelli reasoning).
- `src/main.py`: lettura di `rm_config.get("temperature")` con conversione condizionale a `float` — se il campo è assente dal YAML, passa `None` a `GeminiInterface`.
- `config/llm_models/risk_manager.yaml`: rimossa la riga `temperature: 0.2`. Il Risk Manager usa ora il default Gemini (`1.0`).

### Documentazione

- `docs/config.md`: rimosso `temperature` dal blocco YAML di `risk_manager.yaml`; aggiunta nota nella sezione "Note" che spiega perché Gemini 3.x omette il parametro e la retrocompatibilità dell'interfaccia.
- `dev_support/notes.md`: nota sul `temperature` di Gemini marcata come risolta.

## 1.24.0 — 2026-06-08

### Aggiunto

- `src/core/exceptions.py`: nuova eccezione `OrderReplacementError(ExchangeError)` con attributo `cancelled_order_id: str`. Identifica in modo strutturato il caso "ordine cancellato ma sostituzione fallita", senza dipendere dal text-matching sul messaggio di errore.
- `src/core/notifications.py`: nuova funzione `build_unprotected_position_message(symbol, mode, cancelled_order_id)` — produce un alert HTML Telegram con titolo `[ALARM] POSIZIONE SCOPERTA` e istruzione di intervento manuale immediato.
- `src/agents/execution_trader.py`: nuovo ramo `except OrderReplacementError` in `run()` — il report `FAILED` espone `execution_details["unprotected_position"] = True` e `execution_details["cancelled_order_id"]` per permettere al runner di identificare il caso senza string-matching.

### Modificato

- `src/agents/execution_trader.py`: nel ramo `CANCEL_AND_REPLACE_ORDER` di `_execute_order`, `raise RuntimeError(...)` sostituito con `raise OrderReplacementError(...)` per trasportare `cancelled_order_id` in modo tipizzato.
- `src/core/runner.py`: dopo il blocco `if ... was_executed`, aggiunto controllo su `execution_status is FAILED` + flag `unprotected_position` — se presente, invia l'alert Telegram dedicato. Aggiunto `ExecutionStatus` agli import da `src.core.contracts`.

### Test

- `tests/core/test_notifications.py`: nuovo test `test_build_unprotected_position_message_contains_key_fields` — verifica presenza di simbolo, id ordine e parole chiave di allarme.
- `tests/agents/test_execution_trader.py`: `test_cancel_and_replace_partial_failure_returns_failed` aggiornato — verifica che `execution_details["unprotected_position"]` sia `True` e `cancelled_order_id` sia `"999"`.
- `tests/core/test_runner.py`: due nuovi test — `test_run_sends_unprotected_position_alert_when_flag_set` (alert inviato con flag attivo) e `test_run_does_not_send_unprotected_alert_on_normal_failed` (nessun alert su FAILED normale senza flag).

### Documentazione

- `docs/observability.md`: nuova riga `[ALARM] POSIZIONE SCOPERTA` nella tabella notifiche Telegram; aggiunto blocco di esempio del messaggio.
- `docs/decision_logic.md`: sezione "Execution Trader" — aggiunta nota sul comportamento del `CANCEL_AND_REPLACE_ORDER` parzialmente fallito e sul conseguente alert Telegram.

## 1.23.1 — 2026-06-07

### Modificato

- `src/core/runner.py`: `_maybe_apply_breakeven` ora controlla il kill switch come prima istruzione — se `KILL_SWITCH=1`, logga un DEBUG e ritorna senza toccare l'exchange. Rende il freno d'emergenza coerente: con kill switch attivo nessuna scrittura raggiunge l'exchange (né ordini dall'Execution Trader, né modifiche OCO dal breakeven).

### Test

- `tests/core/test_runner.py`: nuovo test `test_breakeven_not_triggered_when_kill_switch_active` — verifica che con `kill_switch=True` e condizioni di breakeven tutte soddisfatte, `cancel_oco` e `place_oco_sell` non vengano chiamati.

### Documentazione

- `docs/decision_logic.md`: sezione "Breakeven automatico" — aggiunta nota che il meccanismo viene saltato con kill switch attivo. Sezione "Kill switch" — aggiornata per precisare che con kill switch attivo nessuna scrittura raggiunge l'exchange, incluso il breakeven automatico.
- `docs/config.md`: descrizione di `breakeven_trigger_pct` — aggiunta nota che il breakeven non viene eseguito se il kill switch è attivo.

## 1.23.0 — 2026-05-25

### Aggiunto

- `config/trading.yaml`: nuovo parametro `oco_review_interval_hours: 24.0` — ore trascorse dall'apertura di un OCO oltre le quali si attiva la revisione obbligatoria.
- `src/core/contracts.py`: nuovo campo `oco_review_required: bool = False` in `TradingCycleInput` e `DecisionMakerInput`.
- `src/core/runner.py`: nuovo metodo `_is_oco_review_required(portfolio)` — restituisce `True` se almeno un ordine con `orderListId != -1` ha `age_hours >= oco_review_interval_hours`. Il flag viene calcolato in `_build_cycle_input` e inserito nel `TradingCycleInput`.
- `config/prompts/decision_maker.md` (REGOLE OPERATIVE): nuova regola — quando `oco_review_required` è `true`, il DM deve valutare esplicitamente i livelli TP/SL nella `reason`; un HOLD silenzioso non è ammesso.
- `config/prompts/decision_maker.md` (DATI DISPONIBILI — Timing operativo): descrizione del campo `oco_review_required`.

### Modificato

- `src/core/runner.py`: `__init__` legge `oco_review_interval_hours` dal config e lo salva in `self._oco_review_interval_hours` (fallback `24.0`).
- `src/core/workflow.py`: `DecisionMakerInput` ora riceve `oco_review_required=cycle_input.oco_review_required`.
- `src/agents/decision_maker.py`: `_build_user_payload` include `oco_review_required` nel dict JSON inviato al modello.
- `docs/config.md`: aggiornato il blocco YAML con `oco_review_interval_hours`; aggiunta descrizione del parametro.
- `docs/decision_logic.md`: aggiunta riga nella sezione Decision Maker che descrive `oco_review_required` e il suo effetto sul prompt.

### Test

- `tests/core/test_runner.py`: 5 nuovi test su `_is_oco_review_required` (True sopra soglia, False sotto soglia, False senza OCO, False senza ordini) + 1 test end-to-end su `_build_cycle_input` che verifica il flag nel `TradingCycleInput`.
- `tests/core/test_workflow.py`: nuovo test `test_workflow_passes_oco_review_required_to_decision_maker` con capturing class.
- `tests/agents/test_decision_maker.py`: 2 nuovi test su `_build_user_payload` — `oco_review_required=True` nel payload, e default `False`.

---

## 1.22.0 — 2026-05-25

### Aggiunto

- `src/core/contracts.py`: nuovo campo `current_price: float | None = None` in `DecisionMakerInput`. Consente al DM di stimare il valore notional degli ordini senza dover inferire il prezzo dall'analisi testuale del Market Analyst.
- `config/prompts/decision_maker.md` (REGOLE OPERATIVE): nuova regola speculare al limite minimo — il DM deve verificare che `quantity × current_price ≤ max_order_notional_usdc` prima di proporre, con formula esplicita per la quantità massima. L'obiettivo è eliminare i cicli sprecati per correzioni del Risk Manager.
- `config/prompts/decision_maker.md` (DATI DISPONIBILI — Vincoli operativi): descrizione del nuovo campo `current_price`.

### Modificato

- `src/core/workflow.py`: `DecisionMakerInput` ora riceve `current_price=cycle_input.market_data.price`.
- `src/agents/decision_maker.py`: `_build_user_payload` include `current_price` nel dict JSON inviato al modello.
- `docs/decision_logic.md`: aggiunta riga nella sezione Decision Maker che descrive `current_price` e il suo scopo.

### Test

- `tests/core/test_workflow.py`: aggiunto assert su `current_price` nel `DummyDecisionMaker` e nuovo test `test_workflow_passes_current_price_to_decision_maker` con capturing class.
- `tests/agents/test_decision_maker.py`: due nuovi test su `_build_user_payload` — `current_price` presente nel payload con valore corretto, e `None` quando non impostato.

---

## 1.21.0 — 2026-05-25

### Aggiunto

- `src/core/runner.py`: nuovo metodo `_maybe_apply_breakeven`. A ogni ciclo, dopo `_augment_portfolio_with_open_position` e prima del pre-check, verifica se `unrealized_pnl_pct >= breakeven_trigger_pct`, se è presente un OCO attivo (LIMIT_MAKER + STOP_LOSS_LIMIT con stesso `orderListId`) e se lo SL è ancora sotto `avg_entry_price`. Se tutte le condizioni sono soddisfatte: cancella l'OCO esistente, piazza un nuovo OCO con lo stesso TP e lo SL trigger = `avg_entry_price`, ricarica `portfolio.open_orders` con dati freschi. Gli errori vengono loggati come WARNING senza bloccare il ciclo.
- `config/trading.yaml`: nuovo parametro `breakeven_trigger_pct: 2.0` — soglia percentuale di profitto non realizzato oltre cui si attiva il breakeven automatico.
- `src/integrations/exchange/base_exchange_client.py`: nuovo metodo astratto `cancel_oco(symbol, order_list_id)` per cancellare un intero gruppo OCO tramite `orderListId`.
- `src/integrations/exchange/binance_client.py`: implementazione di `cancel_oco` tramite `client.cancel_order_list(symbol, orderListId)`, decorata con `@_binance_retry`.

### Modificato

- `src/core/runner.py`: `__init__` ora legge `breakeven_trigger_pct` dal config e lo salva in `self._breakeven_trigger_pct` (fallback `2.0`). `_run_single_cycle` chiama `_maybe_apply_breakeven` dopo `_augment_portfolio_with_open_position`.
- `docs/config.md`: aggiornato il blocco YAML di `config/trading.yaml` con il nuovo campo; aggiornata la descrizione di `max_order_notional_usdc` con il fallback corretto (`500.0`); aggiunta la descrizione di `breakeven_trigger_pct`.
- `docs/decision_logic.md`: aggiunta sezione "Breakeven automatico" prima del pre-check, con descrizione del flusso e delle condizioni di attivazione.

### Test

- `tests/core/test_runner.py`: 7 nuovi test su `_maybe_apply_breakeven` — attivazione quando tutte le condizioni sono soddisfatte (verifica `cancel_oco` + `place_oco_sell`), non attivazione se `pnl_pct` è None, sotto soglia, senza OCO, con SL già sopra entry o uguale a entry, eccezione non bloccante con warning.
- `tests/integrations/exchange/test_binance_client.py`: 2 nuovi test su `cancel_oco` — chiamata corretta a `cancel_order_list` con i parametri attesi, retry su `BinanceRequestException`.

---

## 1.20.0 — 2026-05-25

### Aggiunto

- `src/core/contracts.py`: nuovo campo `unrealized_pnl_usdc: float | None = None` in `PortfolioState`. Rappresenta il P&L non realizzato in USDC al prezzo corrente, calcolato come `(price - avg_entry_price) * qty_total`.
- `config/prompts/decision_maker.md`: descrizione del nuovo campo `unrealized_pnl_usdc` nella sezione `📊 DATI DISPONIBILI`. Aggiunta regola esplicita nella sezione `🛡️ REGOLE OPERATIVE` che vieta al Decision Maker di calcolare il P&L autonomamente: deve usare esclusivamente i valori forniti dal sistema.

### Modificato

- `src/core/runner.py`: `_augment_portfolio_with_open_position` ora popola anche `portfolio.unrealized_pnl_usdc` insieme a `unrealized_pnl_pct`.
- `src/core/runner.py` (bug fix): corretto il valore di fallback di `max_order_notional_usdc` da `100.0` a `500.0` in `_build_cycle_input`. Il default sbagliato bloccava ordini legittimi quando il file YAML non veniva letto correttamente.

### Test

- `tests/core/test_runner.py`: aggiornati `test_augment_portfolio_populates_avg_entry_and_unrealized_pnl` e `test_augment_portfolio_leaves_fields_none_without_open_position` per includere assert su `unrealized_pnl_usdc`. Aggiunto `test_augment_portfolio_unrealized_pnl_usdc_negative_when_in_loss` per coprire il caso P&L negativo (price < avg_entry_price).

---

## 1.19.0 — 2026-05-20

### Aggiunto

- `src/core/circuit_breaker.py`: nuovo modulo con la classe `CircuitBreaker` e l'helper `build_error_signature`. Il breaker conta errori consecutivi identici (stesso `type(exc).__name__ + str(exc)`) e si trippa al raggiungimento della soglia (default 3). `build_error_signature` riconosce le `CycleExecutionError` e usa l'eccezione originale per la signature, così errori di workflow con stesso `exc.original` vengono confrontati correttamente.
- `src/core/notifications.py`: nuova funzione `build_circuit_breaker_message(symbol, error_signature, threshold)` per la notifica Telegram di trip del circuit breaker. Tronca la signature a 200 caratteri di default per non sforare i limiti Telegram.
- `src/core/runner.py`: integrato `CircuitBreaker` nel `TradingRunner`. Nuovo parametro opzionale `circuit_breaker` nel costruttore (di default ne istanzia uno proprio). Il main loop controlla `is_tripped()` prima di ogni ciclo: se trippato, salta `_run_single_cycle`, aggiorna heartbeat, chiama `maybe_log_paused_status` (log reminder ogni ora) e dorme per `cycle_interval_seconds`. `_run_single_cycle` chiama `record_success()` dopo un ciclo riuscito e `_handle_circuit_breaker(exc)` in tutti e tre i rami `except`, che invia la notifica Telegram `[ALARM] CIRCUIT BREAKER TRIPPED` UNA SOLA volta nell'istante in cui scatta.

### Modificato

- `src/core/runner.py`: rimosso il `raise` finale dal ramo `except Exception` di `_run_single_cycle`. Anche i bug imprevisti (es. `AttributeError`, `TypeError` fuori dal workflow) sono ora gestiti dal circuit breaker invece di propagarsi e far crashare il processo. Chiude definitivamente lo scenario di crash loop Docker: qualunque sia il tipo di errore, dopo 3 ripetizioni identiche il bot va in pausa e attende riavvio manuale. I bug imprevisti vengono comunque notificati su Telegram come `Cycle ERROR` con `correlation_id`.
- `tests/core/test_runner.py`: rinominato e riscritto `test_unexpected_exception_propagates_from_run_single_cycle` in `test_unexpected_exception_does_not_propagate_from_run_single_cycle` (l'AttributeError ora viene catturato e incrementa il counter del breaker). Riscritto `test_unexpected_exception_stops_run_loop_after_notifying` in `test_unexpected_exception_repeated_trips_circuit_breaker_and_pauses_loop` (verifica che 3 errori identici scattino il breaker e che i cicli successivi vengano saltati).
- `docs/observability.md`: nuova sezione "Circuit breaker" con descrizione di trigger, comportamento, signature degli errori e comando di ripristino manuale. Aggiunta riga `[ALARM] CIRCUIT BREAKER TRIPPED` nella tabella delle notifiche Telegram.
- `docs/deploy.md`: nota sul `docker compose restart` come comando di ripristino dopo trip del circuit breaker.
- `docs/repo_structure.md`: aggiunto `circuit_breaker.py` sotto `src/core/` e aggiornata la descrizione di `exceptions.py` per includere `CycleExecutionError`.

### Test

- `tests/core/test_circuit_breaker.py` (nuovo): 11 test che coprono incremento del counter, reset su signature diversa, reset su `record_success`, `record_error` ritorna True solo all'istante dello scatto, `record_success` no-op dopo trip, `maybe_log_paused_status` logga immediatamente la prima volta e poi rispetta l'intervallo, no-op quando non trippato, `build_error_signature` su `Exception` base e su `CycleExecutionError` (unwrap a `exc.original`).
- `tests/core/test_runner.py`: 4 nuovi test sul circuit breaker integrato — 3 errori identici scatenano il breaker con 1 sola notifica Telegram dedicata, 3 errori diversi non scattano, un ciclo riuscito resetta il counter, quando il breaker è trippato il main loop salta i cicli ma continua ad aggiornare l'heartbeat.
- `tests/core/test_notifications.py`: 2 nuovi test su `build_circuit_breaker_message` (campi chiave e troncamento della signature lunga).

---

## 1.18.0 — 2026-05-20

### Aggiunto

- `docker-compose.yaml`: aggiunto `stop_grace_period: 60s` al servizio `trading-bot`. Il default Docker di 10s era troppo breve: un ciclo LLM+Binance può durare 30-40s, quindi il signal handler in `src/core/runner.py` (SIGTERM) non riusciva a completare il ciclo in corso e `SIGKILL` interrompeva tutto senza log "Shutdown" né notifica Telegram di stop.
- `src/core/exceptions.py`: nuova classe `CycleExecutionError(MdkTradingError)` che trasporta `original`, `market_analysis`, `trade_proposal` e `risk_assessment` opzionali per portare con sé i risultati parziali quando un ciclo fallisce a metà del workflow.
- `src/utils/event_logger.py`: `log_error` esteso con tre nuovi parametri opzionali `market_analysis`, `trade_proposal`, `risk_assessment`. Quando passati, vengono serializzati nel record JSONL con `dataclasses.asdict` invece di restare a `null`. Permette il debug post-mortem dei cicli falliti senza perdere ciò che gli agenti avevano già prodotto.
- `docs/observability.md`: aggiornato l'esempio di record di errore per mostrare i campi parziali popolati e documentato il nuovo comportamento del `log_error`.
- `docs/deploy.md`: nota sul nuovo `stop_grace_period: 60s` nella sezione "Fermare il bot".

### Modificato

- `src/core/workflow.py`: ogni step di `TradingWorkflow.run_cycle` (Market Analyst, Decision Maker, Risk Manager, Execution Trader) è ora avvolto in un `try/except` che cattura `Exception` e ri-solleva `CycleExecutionError` con i parziali già prodotti dagli step precedenti.
- `src/core/runner.py`: aggiunto un branch `except CycleExecutionError` dedicato in `_run_single_cycle` (prima del branch generico `MdkTradingError`/`OSError`). Estrae i parziali dall'eccezione e li passa a `event_logger.log_error`. Gli altri due rami `except` (errore operativo fuori workflow e bug imprevisto) restano invariati.

### Corretto

- `tests/test_main.py`: aggiunto `@patch("src.main.configure_logging")` a tutti gli 8 test che chiamano `main()`. Senza il patch, `main()` eseguiva davvero `configure_logging` e attaccava al logger `mdk_crypto_trading` un `RotatingFileHandler` puntato a `logs/mdk_crypto_trading.log` (path di default), che restava vivo per l'intera sessione pytest e raccoglieva tutti i warning dei test successivi (es. righe `MagicMock` nel log di produzione). Ora i test sono isolati dal file di log reale.

### Test

- `tests/core/test_workflow.py`: 4 nuovi test che verificano che `TradingWorkflow.run_cycle` sollevi `CycleExecutionError` con i parziali corretti quando rispettivamente Market Analyst, Decision Maker, Risk Manager o Execution Trader falliscono.
- `tests/utils/test_event_logger.py`: nuovo test `test_log_error_serializes_partial_results` che verifica la serializzazione corretta di `market_analysis`/`trade_proposal` nel JSONL quando vengono passati a `log_error`.
- `tests/core/test_runner.py`: nuovo test `test_run_passes_partial_results_to_log_error_on_cycle_execution_error` che simula una `CycleExecutionError` e verifica che il runner passi `str(exc.original)` come `error` e i tre parziali agli omonimi kwargs di `log_error`.

---

## 1.17.1 — 2026-05-20

### Corretto

- `src/integrations/exchange/binance_client.py`: aggiornato `_place_oco_sell_with_retry` ai nuovi parametri OCO di Binance (endpoint `/orderList/oco`). Sostituiti `price`/`stopPrice`/`stopLimitPrice`/`stopLimitTimeInForce` con `aboveType="LIMIT_MAKER"` + `abovePrice` (take profit) e `belowType="STOP_LOSS_LIMIT"` + `belowPrice` + `belowStopPrice` + `belowTimeInForce="GTC"` (stop loss). La firma pubblica di `place_oco_sell` e il calcolo di `sl_limit_price = sl_stop_price * 0.995` restano invariati. Fix dell'errore `APIError(code=-1102): Mandatory parameter 'aboveType' was not sent`.
- `tests/integrations/exchange/test_binance_client.py`: aggiornati i 4 test OCO (`test_place_oco_sell_calls_create_oco_order_with_correct_params`, `test_place_oco_sell_quantizes_prices`, `test_place_oco_sell_passes_list_client_order_id`, `test_place_oco_sell_retry_uses_same_list_client_order_id`) ai nuovi nomi dei parametri e aggiunte assertion su `aboveType`/`belowType`.
- `docs/api_endpoints.md`: aggiornato endpoint OCO da `/api/v3/order/oco` a `/api/v3/orderList/oco`.

---

## 1.17.0 — 2026-05-13

### Aggiunto

- `src/core/notifications.py`: aggiunto ramo dedicato a `SELL_OCO` in `build_order_notification`. In precedenza gli ordini OCO cadevano nel ramo `LIMIT` mostrando solo il TP e ignorando lo stop loss. Ora la notifica Telegram per `SELL_OCO` include `TP Price` (prezzo take profit), `SL Stop` (prezzo trigger stop loss) e `Est. Value` (controvalore stimato), oltre ai campi comuni già presenti.
- `tests/core/test_notifications.py`: aggiunti `test_build_order_notification_sell_oco_shows_tp_and_sl` (verifica che TP, SL e controvalore compaiano correttamente) e `test_build_order_notification_sell_oco_handles_missing_fields` (verifica che la notifica non crashi se `price` o `sl_stop_price` sono `None`).

### Modificato

- `config/prompts/decision_maker.md`: rimossi i valori percentuali esemplificativi dalla guida alle quantità frazionali (`2-3 tranche da 30-50%` per scaling in, `tipicamente 30-50% della posizione` e `+10/+15% dal prezzo di ingresso` per take profit parziali) e dalla guida all'uso di `unrealized_pnl_pct` (soglia `≥ +10/15%`). Il DM decide autonomamente le proporzioni in base al contesto, senza ancore numeriche rigide.

---

## 1.16.0 — 2026-05-13

### Aggiunto

- `src/integrations/exchange/binance_client.py`: aggiunto helper di modulo `_add_age_to_orders(orders)` che calcola `age_hours` (arrotondato a 1 decimale) per ogni ordine aperto con campo `time` valido (epoch ms Binance). Viene chiamato in `_get_portfolio_state_with_retry` subito dopo `get_open_orders`: gli ordini aperti nel `PortfolioState` ora includono sempre `age_hours`, che il Decision Maker può usare per rivalutare o cancellare `LIMIT` fermi da troppo tempo.
- `src/integrations/exchange/binance_client.py`: rinominato `_get_hourly_closes` in `_get_hourly_ohlc`. Il nuovo metodo restituisce un dict `{"highs": [...], "lows": [...], "closes": [...]}` (60 candele 1h). La chiamata in `_get_market_snapshot_with_retry` è aggiornata per passare le tre serie a `compute_indicators_bundle`, che ora calcola anche l'ATR.
- `src/integrations/exchange/binance_client.py`: aumentati i limiti di fetch candele — `candles_4h` da 14 a 50 (~8 giorni di contesto), `candles_1d` da 14 a 30 (~1 mese di contesto).
- `src/utils/indicators.py`: aggiunta funzione `atr(highs, lows, closes, period=14)` che calcola l'Average True Range con lo smoothing classico di Wilder (True Range = max(H-L, |H-Cprev|, |L-Cprev|), poi EWM con α=1/period). Restituisce `None` se le serie hanno lunghezze diverse o i dati sono insufficienti. `compute_indicators_bundle` aggiornato per accettare `highs` e `lows` come kwargs opzionali e include ora `atr` e `atr_prev` tra le 14 chiavi del dict (entrambi `None` se OHLC non forniti). Le 12 chiavi precedenti rimangono invariate.
- `config/prompts/decision_maker.md`: documentato `age_hours` nella sezione `open_orders`, con guida operativa su quando rivalutare o cancellare ordini limite fermi.
- `config/prompts/market_analyst.md`: aggiunti `atr` e `atr_prev` tra gli indicatori disponibili, con spiegazione operativa (ATR↑ → volatilità crescente; ATR↓ → compressione/possibile breakout). Aggiornati i commenti sulle candele 4h (~8 giorni) e 1d (~1 mese).
- `tests/utils/test_indicators.py`: aggiornato `_EXPECTED_BUNDLE_KEYS` a 14 chiavi. Aggiunti test per `atr()`: none su dati insufficienti, none su serie di lunghezza diversa, range costante converge al range, volatilità maggiore produce ATR maggiore. Adattati i test di `compute_indicators_bundle` per coprire sia il caso senza OHLC (atr=None) sia con OHLC (atr popolato).
- `tests/integrations/exchange/test_binance_client.py`: aggiunti 3 test unitari su `_add_age_to_orders` (caso normale, `time` mancante, `time` non numerico), 1 test integrato su `get_portfolio_state` che verifica `age_hours` sugli ordini aperti, 2 test sul flusso ATR (highs/lows passati al bundle; snapshot espone `atr`/`atr_prev`), 1 test che verifica i nuovi limiti candele 4h/1d nelle chiamate a `get_klines`.

---

## 1.15.0 — 2026-05-13

### Aggiunto

- `src/utils/memory_manager.py`: aggiunto metodo pubblico `compute_open_position(symbol)` che sfrutta la coda FIFO interna per calcolare la posizione ancora aperta (lotti BUY non ancora consumati da SELL). Ritorna `{"open_qty": float, "avg_entry_price": float}` con il prezzo medio ponderato FIFO, oppure `None` se non c'è posizione aperta. Per supportarlo, `_walk_fifo` ora restituisce una tupla `(results, lot_queue)` invece della sola lista — tutti i chiamanti interni (`compute_fifo_trades`, `_build_fifo_index`) aggiornati di conseguenza.
- `src/core/contracts.py`: aggiunti due campi opzionali a `PortfolioState`: `avg_entry_price: float | None = None` (prezzo medio di carico FIFO della posizione aperta) e `unrealized_pnl_pct: float | None = None` (P&L non realizzato percentuale rispetto al prezzo corrente). Aggiunti due campi a `PerformanceStats` (entrambi con default `0`): `sells_in_profit: int` e `sells_in_loss: int` (contatori delle ultime 10 SELL FIFO chiuse rispettivamente in profitto e in perdita).
- `src/core/runner.py`: aggiunto helper privato `_augment_portfolio_with_open_position(market_data, portfolio)`, invocato in `_run_single_cycle` subito dopo il fetch del portafoglio e prima di `CycleSkipHandler.try_skip`. Calcola e popola `avg_entry_price` e `unrealized_pnl_pct` sul `PortfolioState` usando `MemoryManager.compute_open_position`. Attivo solo se `portfolio_qty_total > 0` e prezzo corrente disponibile. Completamente difensivo: le conversioni di tipo sono in `try/except (TypeError, ValueError)`, quindi non può mai interrompere il ciclo per dati malformati.
- `src/utils/performance_stats.py`: `build_performance_stats` calcola ora `sells_in_profit` e `sells_in_loss` dalle ultime 10 trade FIFO (`pnl_pct >= 0` → profitto, `< 0` → perdita). `_format_markdown_report` include i due nuovi contatori nella sezione Statistiche del report markdown.
- `config/prompts/decision_maker.md`: documentati `avg_entry_price` e `unrealized_pnl_pct` nella sezione "Portafoglio e posizione". Aggiunto paragrafo operativo che invita il DM a usare `unrealized_pnl_pct` nelle decisioni di take profit parziale (soglia orientativa ≥ +10/15%) e a non mediare al ribasso senza un setup chiaro.
- `config/prompts/performance_reviewer.md`: documentati `sells_in_profit` e `sells_in_loss` nella sezione dati disponibili. Riscritta la definizione di `DRIFTING` per bilanciare la valutazione su entry e uscite: è `DRIFTING` se `sells_in_loss > sells_in_profit` con attività significativa, se ci sono BUY accumulate senza SELL realizzate per più giorni, o se ci sono sequenze di HOLD su segnali forti e il sistema non ha già una posizione in profitto (ignorare nuovi BULLISH per consolidare un guadagno esistente non è più classificato automaticamente come `DRIFTING`). `MISALIGNED` aggiornato per includere il caso di `sells_in_loss` molto superiore a `sells_in_profit` con `realized_pnl_usdc` negativo significativo. Guida ai `suggestions` aggiornata per richiedere consigli anche sulla gestione delle uscite (take profit, stop loss, uso di `SELL_OCO`), non solo sugli ingressi.
- `tests/utils/test_memory_manager.py`: 5 nuovi test per `compute_open_position` — none senza BUY, none dopo SELL totale, single buy, SELL parziale con residuo, media ponderata multi-lot.
- `tests/utils/test_performance_stats.py`: 2 nuovi test per i contatori `sells_in_profit`/`sells_in_loss` (incluso il caso breakeven contato come profitto, simmetrico a `get_performance_summary`). Asserzioni sulla presenza dei due campi nel report markdown aggiunto al test `test_write_performance_report_creates_file`.
- `tests/core/test_runner.py`: 2 nuovi test per `_augment_portfolio_with_open_position` — con posizione aperta e prezzo disponibile i campi vengono popolati correttamente; senza posizione (`portfolio_qty_total == 0`) i campi restano `None` e `compute_open_position` non viene mai chiamato.

---

## 1.14.4 — 2026-05-09

### Aggiunto

- `src/core/exceptions.py` (nuovo file): gerarchia di eccezioni operative del sistema. `MdkTradingError` è la classe base per tutti gli errori attesi; `ExchangeError(MdkTradingError)` rappresenta errori provenienti dall'exchange (API Binance, rete); `LlmError(MdkTradingError, RuntimeError)` rappresenta errori provenienti da un provider LLM. `LlmError` eredita da entrambi `MdkTradingError` e `RuntimeError` per garantire la backward-compatibility con il codice che cattura `RuntimeError` direttamente.
- `src/integrations/llm_interfaces/base_llm_interface.py`: tutti i `raise RuntimeError(...)` sostituiti con `raise LlmError(...)`. I test esistenti che usano `pytest.raises(RuntimeError)` continuano a passare senza modifiche perché `LlmError IS-A RuntimeError`.
- `src/integrations/exchange/binance_client.py`: `get_market_snapshot` e `get_portfolio_state` sono stati refactorati con lo stesso pattern già usato dai metodi di ordine. La logica con retry vive nei nuovi metodi privati `_get_market_snapshot_with_retry` e `_get_portfolio_state_with_retry` (decorati con `@_binance_retry`); i metodi pubblici fungono da wrapper che catturano `BinanceAPIException` / `BinanceRequestException` e li rilanciano come `ExchangeError`. In precedenza, le eccezioni Binance propagavano direttamente al chiamante senza essere wrappate nel tipo interno.
- `src/core/runner.py`: `_run_single_cycle` ora usa due blocchi `except` distinti invece di un unico `except Exception` generico. `except (MdkTradingError, OSError)` cattura gli errori operativi attesi (exchange offline, LLM sovraccarico): logga e continua il loop. `except Exception` cattura i bug imprevisti (es. `AttributeError`, `NameError`): logga, notifica Telegram e ri-lancia. Il metodo `run()` aggiunge un `except Exception` esterno che intercetta il re-raise, logga come critico, invia notifica Telegram e termina il processo pulitamente (Docker lo riavvierà). Aggiornata `_classify_error` per gestire `LlmError` (→ "Risposta LLM non valida") e `ExchangeError` (→ "API esterna non disponibile") in base al nome della classe.
- `src/agents/execution_trader.py`: il `except Exception` nel metodo `run()` è stato ristretto a `except (ValueError, RuntimeError, ExchangeError)`. `RuntimeError` copre il caso critico `CANCEL_AND_REPLACE` parziale; `ExchangeError` copre gli errori Binance dai metodi `place_*`; `ValueError` copre le validazioni input. Un'eccezione imprevista di tipo diverso ora propaga correttamente al chiamante anziché essere inghiottita silenziosamente.
- `tests/integrations/llm_interfaces/test_base_llm_interface.py`: aggiunti `test_llm_error_is_instance_of_runtime_error` (verifica backward-compat), `test_llm_error_raised_on_empty_response` e `test_llm_error_raised_on_non_retryable_provider_error`.
- `tests/integrations/exchange/test_binance_client.py`: importato `ExchangeError`. `test_get_market_snapshot_no_retry_on_client_error` aggiornato: ora si aspetta `ExchangeError` invece di `BinanceAPIException`. Aggiunti `test_get_market_snapshot_raises_exchange_error_after_all_retries` e `test_get_portfolio_state_raises_exchange_error_on_binance_exception`.
- `tests/core/test_runner.py`: importati `ExchangeError`, `LlmError`, `MdkTradingError`. `test_run_logs_error_on_exception` rinominato in `test_run_logs_error_on_operational_exception` e aggiornato per usare `ExchangeError` (errore operativo che non interrompe il loop). `test_run_sends_error_notification_on_exception` rinominato in `test_run_sends_error_notification_on_operational_exception` e aggiornato per usare `LlmError`. I test `test_run_sends_stop_notification` e `test_run_sends_stop_notification_on_sigterm` corretti: aggiunto mock con `was_executed = False` per evitare che il ciclo entri nel ramo notifica-ordine con MagicMock non type-safe. Aggiunti `test_unexpected_exception_propagates_from_run_single_cycle` (verifica che `AttributeError` si propaghi dopo log e notifica) e `test_unexpected_exception_stops_run_loop_after_notifying`. Aggiunti `test_classify_error_llm_error_is_llm_invalid` e `test_classify_error_exchange_error_is_external_api`.
- `docs/repo_structure.md`: aggiunto `exceptions.py` nella sezione `src/core/`.
- `docs/architecture.md`: aggiornate le sezioni `src/core/`, `src/integrations/`, `BinanceClient` e `Orchestrazione` per riflettere la nuova gerarchia di eccezioni e il comportamento differenziato del runner.

---

## 1.14.3 — 2026-05-09

### Corretto

- `src/agents/execution_trader.py`: il guardrail percentuale sul portafoglio (guardrail #3 in `_validate_guardrails`) usava `portfolio.usdc_value` come denominatore per calcolare la percentuale dell'ordine sul portafoglio. `portfolio.usdc_value` rappresenta il valore in USDC della sola coin posseduta (BTC), non il portafoglio totale. Con un portafoglio da ~5000 USDC in cui ~152 USDC erano investiti in BTC, il guardrail calcolava `152 / 152 = 100%` invece di `152 / 5000 = 3%`, bloccando ogni tentativo di SELL per oltre 5 giorni. Corretto il denominatore in `portfolio.usdc_balance + portfolio.usdc_value` (USDC liberi + valore coin), che rappresenta il valore totale del portafoglio.
- `tests/agents/test_execution_trader.py`: aggiunto test `test_guardrail_portfolio_pct_uses_total_portfolio_value` che riproduce esattamente il bug di produzione — portafoglio da 5000 USDC (4848 USDC liberi + 152 USDC in BTC), SELL da 152 USDC — e verifica che l'ordine venga eseguito correttamente (3% del portafoglio, ampiamente sotto il limite del 70%).

---

## 1.14.2 — 2026-05-07

### Corretto

- `src/integrations/llm_interfaces/anthropic_interface.py`: aggiunto `OverloadedError` (HTTP 529) alla lista `_RETRYABLE_ERRORS`. In precedenza, quando i server Anthropic rispondevano con codice 529 ("Overloaded"), l'errore veniva classificato come `_NON_RETRYABLE_PROVIDER_ERROR` (`APIStatusError`) e convertito in `RuntimeError`, perdendo la semantica di errore transitorio del server. Ora viene riconosciuto correttamente come errore temporaneo e gestito dal layer Tenacity con backoff esponenziale, al pari di `RateLimitError` e `InternalServerError`. Import effettuato da `anthropic._exceptions` (non esportato dal modulo principale nella versione `0.87.0`).
- `tests/integrations/llm_interfaces/test_anthropic_interface.py`: aggiunto test `test_generate_json_retries_on_overloaded_error` che verifica che su `OverloadedError` (HTTP 529) il sistema riprovi automaticamente e recuperi con successo al tentativo successivo. Corretta la docstring del test `test_generate_json_retries_on_internal_server_error` che indicava erroneamente "500/529".

### Aggiunto

- `src/core/runner.py`: aggiunta funzione privata `_classify_error(exc)` che classifica un'eccezione in una delle quattro categorie leggibili: `"API esterna non disponibile"` (Binance 502/503, Anthropic 529, timeout, connessione), `"Rate limit API"` (429), `"Risposta LLM non valida"` (JSON malformato o vuoto), `"Errore interno"` (tutto il resto). La classificazione avviene sul nome della classe e sul testo del messaggio, senza import aggiuntivi delle librerie specifiche dei provider. Aggiornata la chiamata a `build_error_message` per passare la categoria invece del nome grezzo della classe.
- `src/core/notifications.py`: aggiornata `build_error_message` — rimosso il parametro `exc_class`, aggiunto `error_category: str`. La riga `Type: RuntimeError` è sostituita da `Categoria: <categoria>`, permettendo di capire immediatamente dalla notifica Telegram se l'errore è esterno (non preoccuparsi, il bot si recupera da solo) o interno (controllare i log).
- `tests/core/test_notifications.py`: aggiornato `test_build_error_message_contains_correlation_id_and_type` (rinominato in `test_build_error_message_contains_correlation_id_and_category`) per il nuovo signature. Aggiunto `test_build_error_message_shows_external_api_category`.
- `tests/core/test_runner.py`: aggiunti 12 test per `_classify_error` che coprono tutti i casi: `OverloadedError`, `InternalServerError`, `APIConnectionError`, `APITimeoutError`, `BinanceRequestException`, `BinanceAPIException` con status_code 502 e 0, `RateLimitError`, `RuntimeError` con messaggi LLM (risposta vuota, JSON non decodificabile, JSON vuoto), `ValueError` generico, `RuntimeError` generico.

---

## 1.14.1 — 2026-05-04

### Aggiunto

- `src/integrations/exchange/binance_client.py`: idempotency key (`newClientOrderId` / `listClientOrderId`) su `place_market_order`, `place_limit_order` e `place_oco_sell`. Prima di ogni chiamata all'SDK Binance viene generato un UUID v4 univoco nel metodo pubblico e passato al metodo privato interno decorato con `@_binance_retry`. In questo modo tutti i retry usano lo stesso identificativo: se la risposta viene persa per timeout e la chiamata viene ripetuta, Binance riconosce il duplicato e non crea un secondo ordine. I tre metodi hanno ora retry automatico al pari degli altri metodi del client.
- `tests/integrations/exchange/test_binance_client.py`: aggiornati i 4 test esistenti su `place_market_order` e `place_limit_order` per verificare la presenza e la validità del `newClientOrderId` (UUID v4). Aggiunti 3 nuovi test: `test_place_market_order_retry_uses_same_client_order_id`, `test_place_limit_order_retry_uses_same_client_order_id`, `test_place_oco_sell_retry_uses_same_list_client_order_id`, che verificano che tutti i retry di un singolo ordine usino lo stesso identificativo. Aggiunto `test_place_oco_sell_passes_list_client_order_id`. Helper `_assert_valid_uuid4` aggiunto come utility condivisa.
- `docs/architecture.md`: sezione "Retry policy" aggiornata per riflettere il nuovo comportamento (tutti i metodi ora hanno retry; spiegazione del pattern a due livelli UUID → retry).

---

## 1.14.0 — 2026-05-03

### Aggiunto

- `src/core/contracts.py`: aggiunto `SELL_OCO = "SELL_OCO"` a `TradeAction` e campo opzionale `sl_stop_price: float | None = None` a `TradeProposalDetails`.
- `src/integrations/exchange/base_exchange_client.py`: aggiunto metodo astratto `place_oco_sell(symbol, quantity, tp_price, sl_stop_price)`.
- `src/integrations/exchange/binance_client.py`: implementato `place_oco_sell()` con quantize di `tp_price`, `sl_stop_price` e `quantity`; `sl_limit_price` calcolato automaticamente come `sl_stop_price * 0.995`; delega a `create_oco_order()` senza retry per evitare ordini duplicati.
- `src/agents/decision_maker.py`: aggiunto branch `SELL_OCO` in `_parse_trade_proposal()` con validazione di `quantity`, `price` e `sl_stop_price`.
- `src/agents/execution_trader.py`: aggiunti guardrail per `SELL_OCO` (verifica ordinamento `tp > current > sl_stop`, quantità disponibile) e branch in `_execute_order()` che delega a `place_oco_sell()`.
- `config/prompts/decision_maker.md`: documentato `SELL_OCO` nelle regole operative e aggiunto esempio JSON nello schema risposta.
- `config/prompts/risk_manager.md`: aggiunta regola di validazione per `SELL_OCO` e campo `details.sl_stop_price` nella sezione dati disponibili.
- `tests/agents/test_decision_maker.py`: aggiunti test parsing `SELL_OCO` (caso valido, `sl_stop_price` mancante, `sl_stop_price` negativo).
- `tests/agents/test_execution_trader.py`: aggiunti test esecuzione `SELL_OCO` (caso valido, guardrail TP invertito, guardrail qty > free).
- `tests/integrations/exchange/test_binance_client.py`: aggiunti test `place_oco_sell` (parametri corretti, quantize prezzi).

---

## 1.13.16 — 2026-05-02

### Corretto

- `src/core/cycle_skip_handler.py`: `_coerce_float` ora converte `NaN` in `None` tramite `math.isnan`. In precedenza un RSI `NaN` veniva lasciato passare come float valido, aggirando silenziosamente il check `is not None` nel pre-check deterministico.
- `src/core/cycle_skip_handler.py`: `record_completed_cycle` emette ora un `WARNING` esplicito quando lo snapshot salvato ha `rsi=None`, rendendo visibile nei log il fatto che il controllo `rsi_delta` è disattivato invece di fallire silenziosamente.
- `src/integrations/exchange/binance_client.py`: aggiunto `WARNING` diagnostico in `get_market_snapshot` quando `indicators["rsi"]` è `None` ma `indicators["macd"]` non lo è (condizione contraddittoria che indica un problema nel calcolo degli indicatori 1h). Il messaggio include il conteggio delle candele ricevute da `_get_hourly_closes`, permettendo di identificare la causa root alla prossima run.
- `tests/core/test_cycle_skip_handler.py`: aggiunto test per `_coerce_float(NaN) → None` e test che verifica l'emissione del WARNING quando RSI manca nello snapshot.
- `tests/utils/test_cycle_skip.py`: aggiunto test che verifica che `should_skip_cycle` non crashi e ritorni `True` ("unchanged") quando RSI è `None` sia nello snapshot precedente sia nei dati correnti.
- `tests/integrations/exchange/test_binance_client.py`: aggiunto test che verifica l'emissione del WARNING diagnostico quando `compute_indicators_bundle` restituisce RSI `None` con MACD disponibile.

---

## 1.13.15 — 2026-04-29

### Sicurezza / Infrastruttura

- `src/utils/memory_manager.py`: aggiunta validazione regex `_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,20}$")` nel metodo `_symbol_path`. Se il simbolo contiene caratteri non ammessi (es. `..`, `/`, lettere minuscole), viene sollevata `ValueError` prima di costruire il path, eliminando qualsiasi rischio di path traversal verso file al di fuori di `data/memory/`.
- `src/core/runner.py`: aggiunto metodo privato `_touch_heartbeat()` che scrive il timestamp UTC ISO 8601 corrente in `data/heartbeat` come prima operazione di `_run_single_cycle` (viene eseguito anche per i cicli skippati). Gli errori `OSError` vengono ignorati silenziosamente per non bloccare il loop.
- `Dockerfile`: aggiunto `HEALTHCHECK --interval=10m --timeout=10s --start-period=5m --retries=2` basato su `find /app/data/heartbeat -mmin -180`. Il container viene marcato `unhealthy` se il file non viene aggiornato entro 3 ore (margine 2× rispetto al `CYCLE_INTERVAL_SECONDS` attuale di 90 min).
- `.github/workflows/ci.yml`: aggiunto step `Audit dipendenze` che installa `pip-audit` e lo esegue su `requirements.txt` prima dei test. Blocca la CI in presenza di CVE noti nelle dipendenze, complementando Dependabot con feedback immediato ad ogni push.
- `tests/utils/test_memory_manager.py`: aggiunti 3 test per `_symbol_path` (path traversal, lettere minuscole, simbolo valido).
- `tests/core/test_runner.py`: aggiunti 2 test per `_touch_heartbeat` (scrittura file, chiamata ad ogni ciclo).

---

## 1.13.14 — 2026-04-29

### Sicurezza / Infrastruttura

- `Dockerfile`: il container gira ora come utente non privilegiato `app` (UID/GID 1000). Aggiunto `RUN groupadd -g 1000 app && useradd -m -u 1000 -g app app`, creazione di `/app/logs` e `/app/data` con `chown -R app:app /app`, e `USER app` prima del `CMD`. I file in `logs/` e `data/` sono ora leggibili e cancellabili dall'utente SSH standard (UID 1000) senza `sudo`.
- `.github/workflows/ci.yml`: aggiunto blocco `permissions: contents: read` a livello workflow per limitare il `GITHUB_TOKEN` automatico alla sola lettura del repo.
- `docs/deploy.md` — sezione `4a. Clona la repo dalla VM`: sostituita la procedura HTTPS con PAT con la procedura basata su **deploy key SSH read-only** (scope ristretto a un singolo repo, niente token in shell history, revoca istantanea). Inclusa istruzione per configurare `~/.ssh/config`.
- `docs/deploy.md` — sezione `2. Accesso SSH alla VM`: rimossa la raccomandazione di lasciare la passphrase vuota; aggiunta indicazione di impostare una passphrase e usare `ssh-agent` per non reinserirla ogni volta.
- `docs/deploy.md` — sezione `6. Scaricare log ed eventi in locale` e troubleshooting `Permission denied`: rimossi i `sudo` non più necessari grazie al container non-root; aggiunta nota con il `chown -R 1000:1000` una tantum per allineare i file preesistenti creati dal vecchio container root.
- `.gitignore`: aggiunti pattern difensivi nella sezione `Secrets / local config` per prevenire commit accidentali di chiavi e certificati: `*.pem`, `*.key`, `*.p12`, `*.pfx`, `id_rsa`, `id_rsa.pub`, `id_ed25519`, `id_ed25519.pub`, `credentials.json`, `secrets/`.

---

## 1.13.13 — 2026-04-29

### Modificato

- `src/utils/telegram_notifier.py`: il blocco `except` in `send_message` non logga più `str(exc)`, che poteva contenere l'URL completo con il bot token nel path. Gli errori HTTP loggano ora solo lo status code (`HTTP 4xx`); gli altri errori loggano solo il nome della classe dell'eccezione (`exc.__class__.__name__`). Aggiunta funzione helper privata `_redact_token(text, token)` come ultima difesa per rimuovere il token da qualsiasi stringa prima che venga loggata.
- `src/utils/log_utils.py` (nuovo): helper `truncate_for_log(value, max_len=200)` che converte un valore in stringa e la tronca a `max_len` caratteri, aggiungendo un indicatore del numero di caratteri omessi. Evita che blob di risposta LLM (potenzialmente molto grandi) finiscano per intero nei WARNING su file e console Docker.
- `src/agents/base_agent.py`: i due messaggi WARNING in `_call_llm_with_retry` (retry intermedi e tentativo finale) ora usano `truncate_for_log(response)` invece di `response` grezzo. Il contenuto integrale della risposta resta visibile a livello DEBUG (riga già presente).
- `src/integrations/llm_interfaces/base_llm_interface.py`: il WARNING in `_generate_json_once` su `JSONDecodeError` ora usa `truncate_for_log(stripped)` invece di `%r` sulla stringa completa. Rimosso anche l'uso di f-string nel formato del messaggio di log (uniformato a `%s`).
- `src/core/runner.py`: nel blocco `except Exception` di `_run_single_cycle`, viene ora generato un correlation ID corto (`uuid.uuid4().hex[:8]`). Il log locale include il correlation ID (`[cid=XXXXXXXX]`); `EventLogger.log_error` riceve il nuovo campo `correlation_id`; la notifica Telegram viene costruita con `build_error_message(correlation_id=..., exc_class=...)` senza mai passare `str(exc)`.
- `src/utils/event_logger.py`: `log_error` accetta il nuovo parametro opzionale `correlation_id: str = ""`. Il campo viene scritto nel record JSONL (`"correlation_id": "XXXXXXXX"` oppure `null` se assente), permettendo di correlare il record con il log locale e il messaggio Telegram.
- `src/core/notifications.py`: `build_error_message` aggiornato — firma cambiata da `(symbol, error)` a `(symbol, correlation_id, exc_class)`. Il messaggio Telegram ora mostra `Error ID` e `Type` senza mai includere `str(exc)`. Rimossa la dipendenza da `escape_html` (non più necessaria).
- `src/utils/logging_config.py`: `RichHandler` creato con `rich_tracebacks=False` (era `True`). I traceback completi restano disponibili nel file di log via `exc_info=True`; la console Docker è più compatta e non espone stack trace nei log visibili esternamente.
- `tests/core/test_runner.py`: `test_run_logs_error_on_exception` aggiornato per verificare la presenza del campo `correlation_id` (8 caratteri) nella chiamata a `log_error`; `test_run_sends_error_notification_on_exception` aggiornato per verificare che il messaggio Telegram contenga `RuntimeError` e `Error ID:` e **non** contenga `str(exc)`.
- `tests/core/test_notifications.py`: `test_build_error_message_escapes_html` sostituito da `test_build_error_message_contains_correlation_id_and_type` che verifica la nuova firma e il nuovo formato del messaggio.

## 1.13.12 — 2026-04-29

### Aggiunto

- `config/trading.yaml`: nuovo campo `max_order_notional_usdc` (default `100.0`) che definisce il cap massimo di notional per singolo ordine, in USDC.
- `src/core/contracts.py`: `OperationConstraints` esteso con `max_order_notional_usdc: float`; `ExecutionInput` esteso con `portfolio: PortfolioState`, `mandate: InvestmentMandate`, `max_order_notional_usdc: float` e `current_price: float | None`. I nuovi campi portano all'executor tutte le informazioni necessarie per i guardrail deterministici.
- `src/core/runner.py`: `_build_cycle_input` legge `max_order_notional_usdc` dal `trading_config` e lo popola in `OperationConstraints`.
- `src/core/workflow.py`: `run_cycle` passa i nuovi campi (`portfolio`, `mandate`, `current_price`, `max_order_notional_usdc`) a `ExecutionInput`.
- `src/agents/decision_maker.py`: due helper privati `_validate_finite_positive` e `_validate_confidence` validano ogni valore numerico estratto dalla risposta LLM (`quantity`, `price`, `confidence`) controllando `math.isfinite`, positività e range `[0, 1]`. Un valore invalido solleva `ValueError`, che il retry di `BaseLlmAgent._call_llm_with_retry` gestisce già.
- `src/agents/execution_trader.py`: nuovo metodo privato `_validate_guardrails(agent_input)` invocato dopo i check `is_approved` e `is_hold`, prima di `_execute_order`. Implementa 4 controlli in ordine: (1) validazione numerica difensiva di `quantity` e `price`; (2) cap notional massimo per ordine (`quantity × reference_price > max_order_notional_usdc`); (3) cap percentuale sul portafoglio (`notional / portfolio.usdc_value > mandate.max_position_pct`); (4) verifica che l'`order_id` di `CANCEL_AND_REPLACE_ORDER` esista in `portfolio.open_orders`. Ogni blocco produce un `ExecutionReport` con `execution_status=NOT_EXECUTED` e `reason` con prefisso `"Guardrail: …"` riconoscibile nei log eventi.
- `docs/config.md`: aggiunta documentazione del campo `max_order_notional_usdc`.
- Test aggiornati e ampliati: `tests/agents/test_decision_maker.py` (5 nuovi test per validazione `nan`/`inf`/negativo/confidence fuori range), `tests/agents/test_execution_trader.py` (5 nuovi test guardrail + helper `_make_input` aggiornato con i nuovi campi), `tests/core/test_workflow.py` (aggiornati i 3 costruttori di `OperationConstraints`).

Nessun cambio comportamentale per i cicli in cui le proposte LLM sono valide e il notional è entro i limiti. Il guardrail ha l'ultima parola solo in caso di valori anomali o superamento dei cap.

---

## 1.13.11 — 2026-04-29

### Modificato

- `src/core/runner.py`: refactoring puro (Single Responsibility). `TradingRunner` resta il direttore d'orchestra del loop ma delega le decisioni specialistiche a 3 nuovi collaboratori. Il file scende da ~388 a ~230 righe e perde 7 responsabilità mescolate.
- `src/core/cycle_skip_handler.py` (nuovo): classe `CycleSkipHandler` che possiede lo stato cross-cycle (snapshot del ciclo precedente + counter dei salti consecutivi) e la logica di skip deterministico (`try_skip`, `record_completed_cycle`). Le funzioni helper `_build_snapshot` e `_coerce_float` sono state spostate qui.
- `src/core/performance_review_runner.py` (nuovo): classe `PerformanceReviewRunner` che orchestra il giudizio giornaliero (`maybe_run_today`) e legge l'ultimo report markdown (`load_latest_review`).
- `src/core/notifications.py` (nuovo): funzioni pure che costruiscono i messaggi Telegram (`build_startup_message`, `build_stop_message`, `build_error_message`, `build_order_notification`). I dettagli Binance-specific (`cummulativeQuoteQty`/`executedQty` per il prezzo medio dei MARKET order) sono ora incapsulati in `build_order_notification` invece di vivere mescolati con la logica del loop.
- `tests/core/test_runner.py`: aggiornati gli accessi a stato/metodi privati spostati (`runner._previous_snapshot` → `runner._cycle_skip_handler._previous_snapshot`, `runner._load_latest_performance_review()` → `runner._review_runner.load_latest_review()`) e i path di `@patch` per `build_performance_stats` e `load_recent_events` (ora importati da `src.core.performance_review_runner`).
- `docs/architecture.md` e `docs/repo_structure.md`: aggiornati per descrivere la nuova architettura a 4 componenti in `src/core/` (Runner + CycleSkipHandler + PerformanceReviewRunner + notifications).

Nessun cambio di comportamento osservabile dall'esterno: la firma di `TradingRunner.__init__` è invariata, ogni `event_logger.log_*`, ogni messaggio Telegram e ogni file scritto in `data/performance_reports/` sono identici a prima. `src/main.py` non viene toccato.

---

## 1.13.10 — 2026-04-28

### Modificato

- `src/utils/indicators.py`: aggiunta la funzione pubblica `compute_indicators_bundle(closes)` che calcola RSI(14), EMA(21), SMA(50) e MACD sia sulla serie intera sia sulla serie precedente (`closes[:-1]`) e restituisce il dict di 12 chiavi consumato da `MarketDataSnapshot.indicators` (`rsi`, `rsi_prev`, `ema_21`, `ema_21_prev`, ecc.). Le 4 funzioni base (`sma`, `ema`, `rsi`, `macd`) restano invariate.
- `src/integrations/exchange/binance_client.py`: rimosso il metodo privato `_compute_indicators` (~33 righe). Il calcolo degli indicatori non era responsabilità dell'exchange e viveva nel posto sbagliato. `get_market_snapshot` ora fetcha solo i closes 1h e delega tutto il calcolo a `indicators.compute_indicators_bundle`. `_get_hourly_closes` resta dov'è (è exchange-specific).
- `src/integrations/exchange/binance_client.py`: aggiunto `@_binance_retry` a `cancel_order`. L'operazione è idempotente lato Binance (cancellare due volte un ordine inesistente è innocuo), quindi il retry è sicuro e uniforma il comportamento agli altri metodi di lettura.
- `src/integrations/exchange/binance_client.py`: aggiunto sopra `place_market_order` e `place_limit_order` un commento che spiega esplicitamente perché **non** hanno retry: senza idempotency key (`newClientOrderId`) un retry su risposta persa per timeout potrebbe creare un secondo ordine duplicato. La gestione di failure transienti sui place order è demandata al chiamante (`ExecutionTraderAgent`).
- `tests/utils/test_indicators.py`: aggiunti 4 test per `compute_indicators_bundle`: presenza di tutte e 12 le chiavi su input sufficiente, coerenza dei valori `*_prev` con il calcolo su `closes[:-1]`, gestione dell'input troppo corto e dell'input vuoto (tutte le chiavi presenti con valore `None`).
- `docs/architecture.md`: aggiornata la descrizione di `get_market_snapshot` (delega del calcolo a `indicators.py`) e introdotta una sezione esplicita sulla retry policy del `BinanceClient` (read + `cancel_order` con retry, place order senza retry e perché). Aggiornata anche la descrizione di `indicators.py` per menzionare `compute_indicators_bundle`.
- `docs/repo_structure.md`: aggiornata la descrizione di `indicators.py` per menzionare `compute_indicators_bundle`.

Nessun cambio di comportamento osservabile dall'esterno: `MarketDataSnapshot.indicators` continua ad essere popolato con esattamente le stesse 12 chiavi e gli stessi valori di prima.

---

## 1.13.9 — 2026-04-28

### Modificato

- `src/agents/base_agent.py`: introdotta una nuova classe intermedia `BaseLlmAgent(BaseAgent)` che applica il pattern **Template Method** ai 4 agenti che dialogano con un LLM. La classe centralizza in un `run` concreto il flusso comune (verifica prompt → lettura prompt da disco → costruzione payload → chiamata LLM con retry sul parsing). Le sottoclassi devono implementare solo `_build_user_payload` (cosa mandare all'LLM) e `_parse_response` (come interpretare la risposta). `_call_llm_with_retry` è stato spostato da `BaseAgent` a `BaseLlmAgent`, perché era usato solo dagli agenti LLM. `BaseAgent` resta minimale (nome, prompt opzionale, logger, firma astratta di `run`) ed è ancora estesa direttamente da `ExecutionTraderAgent` (l'unico agente non-LLM).
- `src/agents/market_analyst.py`, `src/agents/decision_maker.py`, `src/agents/risk_manager.py`, `src/agents/performance_reviewer.py`: i 4 agenti LLM ora estendono `BaseLlmAgent` invece di `BaseAgent`. Rimosso il metodo `run` (ora ereditato dal template) e l'assegnazione `self._llm = llm` (ora gestita dalla base). Ogni agente espone solo `__init__` (con `name`, `prompt_name`, `llm`), `_build_user_payload` e `_parse_response`. Le funzioni modulo `_parse_market_analysis`, `_parse_trade_proposal`, `_parse_risk_assessment`, `_parse_performance_review` restano invariate (i test le importano direttamente).
- `src/agents/execution_trader.py`: nessuna modifica. Continua a estendere direttamente `BaseAgent`.
- `src/agents/__init__.py`: aggiunto `BaseLlmAgent` agli import e a `__all__`.
- `docs/architecture.md`: aggiornata la descrizione della cartella `src/agents/` per riflettere la nuova gerarchia a due livelli (`BaseAgent` minimale + `BaseLlmAgent` Template Method).
- `docs/decision_logic.md`: aggiornato il riferimento da `BaseAgent._call_llm_with_retry` a `BaseLlmAgent._call_llm_with_retry`.
- `docs/repo_structure.md`: aggiornata la descrizione di `base_agent.py` per menzionare anche `BaseLlmAgent`.

Nessun cambio di firma pubblica e nessun cambio di comportamento osservabile. Ogni agente continua ad essere costruito con `XAgent(llm=...)` e `agent.run(input)` produce lo stesso output di prima. La duplicazione tra i 4 agenti LLM (lettura prompt, costruzione payload, chiamata LLM con retry) è stata eliminata: ora vive solo in `BaseLlmAgent`.

---

## 1.13.8 — 2026-04-28

### Modificato

- `src/integrations/llm_interfaces/base_llm_interface.py`: riscritta da minimal ABC a **Template Method**. Ora `generate_json` è un metodo concreto nella classe base che orchestra retry (`tenacity.Retrying` programmato), chiamata al provider, estrazione testo, controllo risposta vuota, parsing JSON, controllo dict vuoto e wrapping degli errori. Le sottoclassi implementano solo i metodi astratti specifici del provider (`_call_provider`, `_extract_text`, `_log_empty_response`) e possono fare override dell'hook `_strip_response`. Aggiunti gli attributi di classe `_PROVIDER_NAME`, `_RETRYABLE_ERRORS`, `_NON_RETRYABLE_PROVIDER_ERROR` che ogni sottoclasse dichiara.
- `src/integrations/llm_interfaces/anthropic_interface.py`: rimossi `@retry` e blocco `try/except` da `generate_json` (ora gestiti dalla base). Il metodo è stato sostituito da `_call_provider`, `_extract_text` (l'ex funzione modulo, ora metodo della classe), `_log_empty_response` e override di `_strip_response` che chiama la funzione modulo `_strip_markdown_json` (mantenuta come funzione modulo perché importata dai test). `__init__`, `model_name` e `_build_kwargs` invariati.
- `src/integrations/llm_interfaces/openai_interface.py`: rimossi `@retry` e blocco `try/except` da `generate_json`. Aggiunti `_call_provider`, `_extract_text`, `_log_empty_response`. `__init__`, `model_name` e `_build_kwargs` invariati.
- `src/integrations/llm_interfaces/gemini_interface.py`: rimossi `@retry` e blocco `try/except` da `generate_json`. Aggiunti `_call_provider`, `_extract_text`, `_log_empty_response`. `__init__` e `model_name` invariati.
- `docs/architecture.md`: aggiunta nota sul Template Method nella descrizione di `llm_interfaces/`.

Nessun cambio di firma pubblica, di comportamento osservabile o di messaggi di errore. La duplicazione tra le tre interfacce LLM (logica di retry, controllo risposta vuota, parsing JSON, gestione errori) è stata eliminata: ora vive solo nella base.

---

## 1.13.7 — 2026-04-28

### Modificato

- `src/core/contracts.py`, `src/core/runner.py`, `src/core/workflow.py`, `src/agents/decision_maker.py`, `config/prompts/decision_maker.md`, `docs/architecture.md`, `docs/decision_logic.md`: rinominato il campo `ia_memory` in `decision_memory` su `DecisionMakerInput` e `TradingCycleInput`. Il nuovo nome è più preciso: descrive la memoria del Decision Maker, non dell'"IA" in senso generico. Nessun cambio di logica.
- `src/agents/base_agent.py` e i tre agenti che la importano (`market_analyst.py`, `risk_manager.py`, `performance_reviewer.py`) + `tests/agents/test_agent_interfaces.py`: rimosso il prefisso `_` dalla funzione `_ensure_list_of_str`, rinominata in `ensure_list_of_str`. La funzione è importata da tre moduli esterni, quindi il prefisso "privato" era fuorviante. Nessun cambio di comportamento.
- `src/core/__init__.py`: aggiunti agli export pubblici del package `InvestmentMandate`, `MandateAdherence`, `PerformanceStats`, `PerformanceReview`, `PerformanceReviewerInput`, `CycleSkipConfig`, `CycleContextSnapshot`. Erano già definiti in `contracts.py` ma non esposti da `src.core`. Chi importava da `src.core.contracts` può ora importare da `src.core` senza frammentazione.
- `src/integrations/llm_interfaces/base_llm_interface.py`, `anthropic_interface.py`, `openai_interface.py`, `gemini_interface.py`: rimosso il metodo `generate_text` da tutte le interfacce. Non veniva mai chiamato in produzione (solo dai test) e non aggiungeva valore rispetto a `generate_json`. Rimossi anche i relativi test in `tests/integrations/llm_interfaces/`. I test che usavano `generate_text` come veicolo per verificare il comportamento dei kwargs (`temperature`, `max_tokens`, `thinking_effort`, `reasoning_effort`) sono stati convertiti a usare `generate_json`, mantenendo la copertura.

---

## 1.13.6 — 2026-04-28

### Corretto

- `src/core/contracts.py`, `src/core/workflow.py` e `tests/agents/test_execution_trader.py`: ripulito `ExecutionInput` rimuovendo `portfolio`, `constraints` e `current_price`, che non venivano mai letti dall'`ExecutionTraderAgent`. Il contratto ora espone solo i dati davvero usati dall'esecutore, senza creare aspettative false.
- `src/agents/decision_maker.py`: quando il Decision Maker propone `HOLD`, il parser forza sempre `order_type = NONE`, anche se l'LLM restituisce un valore incoerente. Questo allinea `TradeProposal` con il comportamento gia' applicato dall'Execution Trader nei report.
- `config/prompts/decision_maker.md` e `tests/agents/test_decision_maker.py`: aggiornata la documentazione dello schema `HOLD` e aggiunta regressione che verifica la normalizzazione automatica di `order_type` a `NONE`.

---

## 1.13.5 — 2026-04-28

### Corretto

- Allineati i mock dei test ai valori reali di configurazione: `max_position_pct` portato da `100.0` a `70.0` e `max_consecutive_skips` da `5` a `4`. Questo riduce il rischio che la suite passi con vincoli diversi da quelli usati davvero in produzione.
- `tests/agents/test_agent_interfaces.py`: aggiunta copertura anche per `PerformanceReviewerAgent`, sia nel controllo di ereditarietà da `BaseAgent` sia nella verifica del `prompt_path`.
- `tests/core/test_workflow.py`: aggiunti due test sui percorsi reali `RiskDecision.BLOCK` e `RiskDecision.REQUEST_ADJUSTMENT`, usando `ExecutionTraderAgent` reale con exchange mockato. I nuovi test verificano che il workflow completi comunque la sequenza ma non piazzi alcun ordine quando il Risk Manager non approva la proposta.

---

## 1.13.4 — 2026-04-27

### Corretto

- `src/main.py`: aggiunta validazione fail-fast delle API key LLM obbligatorie (`OPENAI_API_KEY`, `CLAUDE_API_KEY`, `GEMINI_API_KEY`) subito al boot. Se una chiave manca, il processo fallisce con un errore chiaro invece di creare i client con stringa vuota e scoprire il problema solo al primo ciclo operativo.
- `tests/test_main.py`: aggiunta regressione per il fail-fast sulle API key mancanti e aggiornato il test dei path LLM per accettare i nuovi percorsi assoluti.
- `src/integrations/llm_interfaces/openai_interface.py` e `src/integrations/llm_interfaces/gemini_interface.py`: allineato `generate_text()` al comportamento gia' usato da Anthropic. Ora una risposta vuota viene loggata e provoca `RuntimeError`, invece di ritornare silenziosamente una stringa vuota.
- `tests/integrations/llm_interfaces/test_openai_interface.py` e `tests/integrations/llm_interfaces/test_gemini_interface.py`: aggiunti test di regressione per verificare warning + `RuntimeError` su risposta vuota in `generate_text()`.
- `src/agents/execution_trader.py` e `src/core/runner.py`: migliorato il logging negli `except Exception` aggiungendo `exc_info=True`, cosi' il traceback completo resta disponibile nei log senza cambiare la logica di fallback.
- `src/utils/config.py`, `src/utils/event_log_reader.py`, `src/main.py` e `src/core/runner.py`: sostituiti i path relativi di default con path assoluti calcolati dalla root del progetto. Questo evita errori di avvio o file non trovati quando il bot viene lanciato da una cartella diversa dalla repo.

---

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
