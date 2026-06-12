# KPI — Indicatori chiave di performance

MDK Crypto Trading misura le proprie performance con **6 KPI ufficiali**. Questo documento definisce cosa misura ciascun KPI, chi lo decide, chi lo calcola e da quando è disponibile.

---

## 📋 Indice

- [Chi decide e chi misura](#chi-decide-e-chi-misura)
- [I 6 KPI](#i-6-kpi)
  - [1. P&L cumulato](#1-pl-cumulato)
  - [2. Win rate](#2-win-rate)
  - [3. Rapporto vincita media / perdita media](#3-rapporto-vincita-media--perdita-media)
  - [4. Numero di trade](#4-numero-di-trade)
  - [5. Rendimento vs buy-and-hold BTC](#5-rendimento-vs-buy-and-hold-btc)
  - [6. Max drawdown](#6-max-drawdown)
- [Benchmark e limiti](#benchmark-e-limiti)
- [Da quando sono disponibili](#da-quando-sono-disponibili)

---

## Chi decide e chi misura

| Ruolo            | Chi                                  |
|------------------|--------------------------------------|
| Definisce i KPI  | Il proprietario del sistema (Chief)  |
| Misura i KPI     | Il sistema (calcolo deterministico)  |
| Valuta i KPI     | Il Performance Reviewer (agente LLM) |

Il Performance Reviewer legge i KPI già calcolati dal sistema e li usa per valutare se il comportamento degli agenti è allineato al mandato. Non ricalcola nulla da solo.

---

## I 6 KPI

### 1. P&L cumulato

**Cosa misura**: il guadagno o la perdita totale realizzati su tutti i trade chiusi dall'inizio dello storico disponibile, espresso in USDC e in percentuale media.

**Come si calcola**: somma del P&L realizzato di ogni vendita, calcolato con il metodo FIFO (First In, First Out). Ogni vendita viene confrontata con il prezzo medio ponderato dei lotti di acquisto corrispondenti.

**Disponibile**: subito, anche sui dati storici già presenti.

---

### 2. Win rate

**Cosa misura**: la percentuale di trade chiusi in profitto sul totale dei trade chiusi.

**Come si calcola**: `(numero di SELL in profitto) / (totale SELL chiuse) × 100`. Una SELL al pareggio conta come profitto.

**Disponibile**: subito, anche sui dati storici già presenti.

---

### 3. Rapporto vincita media / perdita media

**Cosa misura**: quanto guadagna in media un trade vincente rispetto a quanto perde in media un trade perdente.

**Come si calcola**:

- `avg_win_pct`: media percentuale dei trade chiusi in profitto.
- `avg_loss_pct`: media del valore assoluto percentuale dei trade chiusi in perdita.

Un sistema sano ha `avg_win_pct` > `avg_loss_pct`, anche con un win rate inferiore al 50%.

**Disponibile**: subito, anche sui dati storici già presenti.

---

### 4. Numero di trade

**Cosa misura**: quante operazioni di acquisto e vendita sono state eseguite nel periodo analizzato.

**Come si calcola**: conteggio diretto dei cicli con `execution_status = EXECUTED` per BUY e SELL nel periodo.

**Disponibile**: subito, anche sui dati storici già presenti.

---

### 5. Rendimento vs buy-and-hold BTC

**Cosa misura**: se il sistema ha fatto meglio o peggio di tenere semplicemente il BTC fermo dall'inizio al termine del periodo analizzato.

**Come si calcola**:

- `buy_and_hold_return_pct`: variazione percentuale del prezzo BTC dal primo all'ultimo record del periodo.
- `strategy_return_pct`: variazione percentuale del valore totale del portafoglio (cash USDC + valore delle crypto al prezzo corrente) dal primo all'ultimo record del periodo.

**Disponibile**: solo dalla versione 1.27.0 in avanti. Richiede che il sistema abbia già accumulato almeno due record con il campo `equity_usdc` nel periodo analizzato.

---

### 6. Max drawdown

**Cosa misura**: la perdita massima dal picco più alto raggiunto dal portafoglio all'interno del periodo analizzato. Indica il rischio reale sopportato durante il periodo.

**Come si calcola**: per ogni punto della serie storica del valore del portafoglio (`equity_usdc`), si calcola la discesa percentuale dal picco precedente più alto. Il max drawdown è il valore più alto osservato.

**Limite operativo**: **15%**. Se il drawdown supera questo limite, il sistema è fuori mandato.

**Disponibile**: solo dalla versione 1.27.0 in avanti. Richiede che il sistema abbia già accumulato almeno due record con il campo `equity_usdc` nel periodo analizzato.

---

## Benchmark e limiti

| KPI               | Obiettivo                                    | Limite         |
|-------------------|----------------------------------------------|----------------|
| P&L cumulato      | Positivo e crescente                         | —              |
| Win rate          | > 50% come riferimento                       | —              |
| Vincita / perdita | `avg_win_pct` > `avg_loss_pct`               | —              |
| Numero di trade   | Nessun obiettivo numerico fisso              | —              |
| vs buy-and-hold   | Battere il rendimento passivo del BTC        | Benchmark      |
| Max drawdown      | Il più basso possibile                       | **max 15%**    |

Il benchmark principale è **battere il buy-and-hold**: se tenere il BTC fermo avrebbe reso di più, il sistema non sta aggiungendo valore.

---

## Da quando sono disponibili

| KPI                           | Storico pre-1.27.0 | Dalla v1.27.0 in poi |
|-------------------------------|:------------------:|:--------------------:|
| P&L cumulato                  | ✅                 | ✅                   |
| Win rate                      | ✅                 | ✅                   |
| Vincita media / perdita media | ✅                 | ✅                   |
| Numero di trade               | ✅                 | ✅                   |
| Rendimento vs buy-and-hold    | ❌                 | ✅ (dopo 2+ record)  |
| Max drawdown                  | ❌                 | ✅ (dopo 2+ record)  |

I KPI contrassegnati con ❌ per lo storico pre-1.27.0 richiedono la serie temporale del valore totale del portafoglio (`equity_usdc`), che non era registrata prima di questa versione. I dati passati non possono essere recuperati retroattivamente.

---

## 📚 Riferimenti

- **Codice di calcolo**: `src/utils/performance_stats.py`
- **Memoria del sistema**: `src/utils/memory_manager.py` (campo `equity_usdc`)
- **Prompt del Reviewer**: `config/prompts/performance_reviewer.md`
- **Osservabilità**: `docs/observability.md`
