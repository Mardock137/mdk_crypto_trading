# Logica decisionale

Descrive la logica decisionale di MDK Crypto Trading: cosa fa ogni agente, come le decisioni passano da uno all'altro e come vengono gestiti errori e casi limite.

---

## 📋 Indice

- [Flusso delle decisioni](#flusso-delle-decisioni)
- [Market Analyst](#market-analyst)
- [Decision Maker](#decision-maker)
- [Risk Manager](#risk-manager)
- [Execution Trader](#execution-trader)
- [Kill switch](#kill-switch)
- [Normalizzazione e retry su errori LLM](#normalizzazione-e-retry-su-errori-llm)
- [📚 Riferimenti](#-riferimenti)

---

## Flusso delle decisioni

Ogni ciclo operativo segue una catena lineare di 4 passaggi. Ogni agente riceve l'output del precedente e produce un output strutturato per il successivo.

```mermaid
flowchart TD
    MA["Market Analyst"] -->|MarketAnalysis| DM["Decision Maker"]
    DM -->|TradeProposal| RM["Risk Manager"]
    RM -->|RiskAssessment| ET["Execution Trader"]
    ET -->|ExecutionReport| LOG["Log ciclo"]
```

### Pre-check deterministico (opzionale)

Prima della catena di agenti, il runner puo' applicare un pre-check deterministico (zero LLM) che confronta il contesto attuale con lo snapshot del ciclo precedente: se prezzo, RSI, segno MACD e set di ordini aperti sono rimasti entro soglie di tolleranza e l'ultima azione era `HOLD`, il ciclo viene saltato senza chiamare alcun agente. Lo skip e' configurabile via `config/cycle_skip.yaml` (vedi `docs/config.md`) e si disattiva dopo `max_consecutive_skips` consecutivi per garantire che il Decision Maker rivaluti comunque il setup periodicamente. I cicli saltati vengono registrati in `logs/events/` con `cycle_type: "skipped"`.

---

## Market Analyst

Analizza i dati di mercato e produce un segnale. Non decide operazioni.

- **Output**: `market_bias` (BULLISH / BEARISH / NEUTRAL), `signal_strength`, `confidence`, `suggested_action` (LONG_BIAS / SHORT_BIAS / NO_TRADE_BIAS)
- Se i dati sono insufficienti o contraddittori → segnale NEUTRAL

---

## Decision Maker

Riceve il segnale del Market Analyst e formula una proposta operativa usando come bussola il **mandato di investimento** definito in `config/trading.yaml`. Gira su Claude Opus 4.7 con adaptive thinking (`thinking_effort: high`): il modello esegue un ragionamento strutturato interno prima di emettere la proposta JSON.

- **Azioni possibili**: `BUY`, `SELL`, `HOLD`, `CANCEL_AND_REPLACE_ORDER`
- **Tipi di ordine**: `MARKET`, `LIMIT`, `NONE` (solo per HOLD)
- Usa il mandato (drawdown massimo, orizzonte, posizione massima) come vincoli di rischio e contesto strategico. L'obiettivo di generare rendimento sul capitale è parte dell'identità del DM ed è definito nel prompt.
- Valuta esplicitamente memoria (`decision_memory`) e performance (`performance_summary`, `recent_performance`) **prima** di decidere: una sequenza di `HOLD` su mercato non fermo è un indizio di esitazione.
- Riceve anche `latest_performance_review`: il report giornaliero del `Performance Reviewer` con giudizio sull'aderenza al mandato (`ALIGNED`, `DRIFTING`, `MISALIGNED`) e 1-3 suggerimenti concreti. Se il Reviewer segnala `DRIFTING` o `MISALIGNED`, i suggerimenti vanno incorporati attivamente nella decisione.
- Nell'ambiguità propende per l'azione coerente con il mandato, non per un `HOLD` di default. `HOLD` resta legittimo quando il mercato è fermo o i rischi sono concreti.
- Può usare **quantity frazionali** rispetto al portafoglio: non è obbligato a usare tutto il saldo USDC o a vendere sempre l'intera posizione.
- **Scaling in**: quando un setup è chiaro ma vuole ridurre il rischio di timing, può dividere l'ingresso in 2-3 tranche (prima tranche `MARKET BUY`, successive `LIMIT BUY` a prezzi più bassi).
- **Take profit parziali**: quando il prezzo è salito significativamente dall'ingresso, può piazzare un `LIMIT SELL` sopra il prezzo corrente con `quantity` parziale (es. 30-50% della posizione) per monetizzare una parte lasciando correre il resto. Eventuali aggiornamenti del TP nei cicli successivi passano da `CANCEL_AND_REPLACE_ORDER`.
- Lo **stop loss proattivo** non è ancora implementato: gli order type `STOP_LOSS`, `STOP_LOSS_LIMIT`, `TAKE_PROFIT` e `OCO` saranno introdotti in una fase futura. Al momento, se il DM vede rischio ribassista concreto, deve fare `MARKET SELL` (totale o parziale) — non `LIMIT SELL` sotto mercato, che verrebbe eseguito immediatamente.
- Non propone ordini sotto `min_order_usdc`.
- Non propone ordini duplicati se ci sono già ordini aperti sulla stessa coppia.

---

## Risk Manager

Valuta la proposta del Decision Maker rispetto ai vincoli di rischio.

- **Esiti possibili**: `APPROVE`, `BLOCK`, `REQUEST_ADJUSTMENT`
- `APPROVE`: proposta valida e coerente con i vincoli
- `BLOCK`: proposta pericolosa, impossibile o incoerente
- `REQUEST_ADJUSTMENT`: idea valida ma dettagli da correggere
- Verifica: saldo sufficiente, quantità disponibile, ordine sopra il minimo, nessun ordine in conflitto

---

## Execution Trader

Esegue la proposta se approvata. Nessuna decisione strategica.

- Se `risk_decision` non è `APPROVE` → non esegue
- Se l'azione è `HOLD` → non esegue
- Se `CANCEL_AND_REPLACE_ORDER` → cancella l'ordine vecchio, poi piazza il nuovo
- Se l'esecuzione fallisce → segnala `FAILED` nel report

---

## Performance Reviewer

Agente consultivo fuori dalla catena decisionale. Gira **una volta al giorno**, all'inizio del primo ciclo della giornata in cui non esiste già un report in `data/performance_reports/`.

- Il runner chiama `_maybe_run_performance_review()` a inizio ciclo: se il file `YYYY-MM-DD.md` esiste già per oggi, ritorna subito senza costi.
- Altrimenti:
  1. `load_recent_events` legge i log JSONL degli ultimi 7 giorni filtrati per simbolo.
  2. `build_performance_stats` calcola statistiche **deterministiche** (zero LLM): `total_cycles`, `hold_ratio`, `strong_bullish_ignored`, `sell_failed`, `realized_pnl_usdc`, `days_without_executed_trade`, ecc.
  3. `PerformanceReviewerAgent` (Claude Sonnet 4.6) riceve stats + mandato e produce un `PerformanceReview`: summary conciso, `mandate_adherence` (`ALIGNED` / `DRIFTING` / `MISALIGNED`) e 1-3 suggerimenti concreti.
  4. Il risultato viene serializzato in markdown in `data/performance_reports/YYYY-MM-DD.md`.
- Nei cicli successivi, `_load_latest_performance_review` legge il file più recente e lo passa al Decision Maker come stringa (`latest_performance_review`).
- **Errori non bloccano il ciclo**: se il Reviewer fallisce (LLM down, stats non calcolabili, ecc.), viene loggato un warning e il DM riceve stringa vuota come fallback.

---

## Kill switch

Se `KILL_SWITCH=1` nel `.env`, l'Execution Trader blocca qualsiasi operazione e ritorna `NOT_EXECUTED` indipendentemente dalla decisione degli altri agenti. Il resto della catena gira normalmente (analisi, decisione, risk check) ma nessun ordine viene piazzato.

---

## Normalizzazione e retry su errori LLM

Il sistema gestisce gli errori LLM su due livelli distinti.

**Livello 1 — retry API (tenacity, nelle interfacce LLM):**
Ogni interfaccia LLM riprova automaticamente le chiamate API in caso di errori temporanei del provider, con backoff esponenziale (max 3 tentativi):

- `AnthropicInterface`: `RateLimitError`, `APIConnectionError`, `APITimeoutError`, `InternalServerError` (include errori 500 e 529)
- `OpenAiInterface`: `RateLimitError`, `APIConnectionError`, `APITimeoutError`, `InternalServerError`
- `GeminiInterface`: `ServerError`

**Livello 2 — retry parsing (BaseLlmAgent._call_llm_with_retry):**
Prima di validare la risposta JSON, il sistema la normalizza tramite `unwrap_llm_response()`. Questo gestisce i casi in cui il modello restituisce il JSON corretto ma wrappato in un array (es. `[{...}]` invece di `{...}`), oppure risponde con un dict vuoto o un tipo non atteso.

Le interfacce LLM rilevano in anticipo le risposte problematiche e sollevano `RuntimeError` nei seguenti casi:

- risposta vuota o `None` dal provider
- risposta JSON decodificata in un dict vuoto `{}`
- risposta non decodificabile come JSON (con log WARNING della risposta raw)

L'intera operazione — chiamata al modello, normalizzazione e parsing — è racchiusa in un blocco `try/except` che cattura `ValueError`, `KeyError`, `TypeError` e `RuntimeError`. Se qualcosa va storto, il sistema riprova automaticamente fino a un massimo di 4 tentativi. Ad ogni tentativo fallito viene emesso un WARNING con il dettaglio dell'errore e la risposta raw del modello. Se tutti e 4 i tentativi falliscono, il ciclo viene segnato come errore e il sistema passa al ciclo successivo.

---

## 📚 Riferimenti

- **Codice**:
  - `src/core/contracts.py` — strutture dati condivise (MarketAnalysis, TradeProposal, RiskAssessment, ExecutionReport, InvestmentMandate)
  - `src/core/workflow.py` — orchestrazione della catena di agenti
  - `src/agents/` — implementazione dei 4 agenti
  - `src/utils/config.py` — `load_mandate` carica e valida il mandato da `config/trading.yaml`
- **Doc correlati**: `docs/architecture.md`, `docs/hierarchy_and_roles.md`
