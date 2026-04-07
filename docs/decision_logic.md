# 🧠 Logica decisionale

## Flusso delle decisioni

Ogni ciclo operativo segue una catena lineare di 4 passaggi. Ogni agente riceve l'output del precedente e produce un output strutturato per il successivo.

```mermaid
flowchart TD
    MA["Market Analyst"] -->|MarketAnalysis| DM["Decision Maker"]
    DM -->|TradeProposal| RM["Risk Manager"]
    RM -->|RiskAssessment| ET["Execution Trader"]
    ET -->|ExecutionReport| LOG["Log ciclo"]
```

## Market Analyst

Analizza i dati di mercato e produce un segnale. Non decide operazioni.

- **Output**: `market_bias` (BULLISH / BEARISH / NEUTRAL), `signal_strength`, `confidence`, `suggested_action` (LONG_BIAS / SHORT_BIAS / NO_TRADE_BIAS)
- Se i dati sono insufficienti o contraddittori → segnale NEUTRAL

## Decision Maker

Riceve il segnale del Market Analyst e formula una proposta operativa.

- **Azioni possibili**: `BUY`, `SELL`, `HOLD`, `CANCEL_AND_REPLACE_ORDER`
- **Tipi di ordine**: `MARKET`, `LIMIT`, `NONE` (solo per HOLD)
- Se il segnale non è chiaro o i dati sono insufficienti → `HOLD`
- Non propone ordini sotto `min_order_usdc`
- Non propone ordini duplicati se ci sono già ordini aperti sulla stessa coppia

## Risk Manager

Valuta la proposta del Decision Maker rispetto ai vincoli di rischio.

- **Esiti possibili**: `APPROVE`, `BLOCK`, `REQUEST_ADJUSTMENT`
- `APPROVE`: proposta valida e coerente con i vincoli
- `BLOCK`: proposta pericolosa, impossibile o incoerente
- `REQUEST_ADJUSTMENT`: idea valida ma dettagli da correggere
- Verifica: saldo sufficiente, quantità disponibile, ordine sopra il minimo, nessun ordine in conflitto

## Execution Trader

Esegue la proposta se approvata. Nessuna decisione strategica.

- Se `risk_decision` non è `APPROVE` → non esegue
- Se l'azione è `HOLD` → non esegue
- Se `CANCEL_AND_REPLACE_ORDER` → cancella l'ordine vecchio, poi piazza il nuovo
- Se l'esecuzione fallisce → segnala `FAILED` nel report

## Kill switch

Se `KILL_SWITCH=1` nel `.env`, l'Execution Trader blocca qualsiasi operazione e ritorna `NOT_EXECUTED` indipendentemente dalla decisione degli altri agenti. Il resto della catena gira normalmente (analisi, decisione, risk check) ma nessun ordine viene piazzato.

## Normalizzazione e retry su errori LLM

Prima di validare la risposta JSON di un agente LLM, il sistema la normalizza tramite `unwrap_llm_response()`. Questo gestisce i casi in cui il modello restituisce il JSON corretto ma wrappato in un array (es. `[{...}]` invece di `{...}`), oppure risponde con un dict vuoto o un tipo non atteso.

Se dopo la normalizzazione la risposta risulta comunque non valida, il sistema riprova automaticamente una seconda volta. Se anche il secondo tentativo fallisce, il ciclo viene segnato come errore e il sistema passa al ciclo successivo.
