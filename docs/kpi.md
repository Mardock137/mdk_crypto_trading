# KPIs — Key Performance Indicators

MDK Crypto Trading measures its performance with **6 official KPIs**. This document defines what each KPI measures, who decides it, who computes it, and since when it is available.

---

## 📋 Table of Contents

- [Who decides and who measures](#who-decides-and-who-measures)
- [The 6 KPIs](#the-6-kpis)
  - [1. Cumulative P&L](#1-cumulative-pl)
  - [2. Win rate](#2-win-rate)
  - [3. Average win / average loss ratio](#3-average-win--average-loss-ratio)
  - [4. Number of trades](#4-number-of-trades)
  - [5. Return vs BTC buy-and-hold](#5-return-vs-btc-buy-and-hold)
  - [6. Max drawdown](#6-max-drawdown)
- [Benchmarks and limits](#benchmarks-and-limits)
- [Availability since](#availability-since)

---

## Who decides and who measures

| Role              | Who                                    |
|-------------------|----------------------------------------|
| Defines the KPIs  | The system owner                       |
| Measures the KPIs | The system (deterministic computation) |
| Evaluates the KPIs| The Performance Reviewer (LLM agent)   |

The Performance Reviewer reads the KPIs already computed by the system and uses them to assess whether the agents' behavior is aligned with the mandate. It does not recompute anything on its own.

---

## The 6 KPIs

### 1. Cumulative P&L

**What it measures**: the total profit or loss realized across all trades closed since the beginning of the available history, expressed in USDC and as an average percentage.

**How it's computed**: sum of the realized P&L of each sale, computed with the FIFO (First In, First Out) method. Each sale is compared against the weighted average price of the corresponding purchase lots.

**Available**: immediately, even on already existing historical data.

---

### 2. Win rate

**What it measures**: the percentage of trades closed in profit out of all closed trades.

**How it's computed**: `(number of profitable SELLs) / (total closed SELLs) × 100`. A breakeven SELL counts as a profit.

**Available**: immediately, even on already existing historical data.

---

### 3. Average win / average loss ratio

**What it measures**: how much a winning trade earns on average compared to how much a losing trade loses on average.

**How it's computed**:

- `avg_win_pct`: average percentage of trades closed in profit.
- `avg_loss_pct`: average absolute percentage value of trades closed in loss.

A healthy system has `avg_win_pct` > `avg_loss_pct`, even with a win rate below 50%.

**Available**: immediately, even on already existing historical data.

---

### 4. Number of trades

**What it measures**: how many buy and sell operations were executed in the analyzed period.

**How it's computed**: direct count of cycles with `execution_status = EXECUTED` for BUY and SELL in the period.

**Available**: immediately, even on already existing historical data.

---

### 5. Return vs BTC buy-and-hold

**What it measures**: whether the system performed better or worse than simply holding BTC from the start to the end of the analyzed period.

**How it's computed**:

- `buy_and_hold_return_pct`: percentage change in the BTC price from the first to the last record of the period.
- `strategy_return_pct`: percentage change in the total portfolio value (USDC cash + crypto value at the current price) from the first to the last record of the period.

**Available**: only from version 1.27.0 onward. Requires the system to have already accumulated at least two records with the `equity_usdc` field in the analyzed period.

---

### 6. Max drawdown

**What it measures**: the maximum loss from the highest peak reached by the portfolio within the analyzed period. Indicates the actual risk incurred during the period.

**How it's computed**: for every point in the portfolio value's historical series (`equity_usdc`), the percentage decline from the highest previous peak is computed. The max drawdown is the highest value observed.

**Operational limit**: **15%**. If the drawdown exceeds this limit, the system is out of mandate.

**Available**: only from version 1.27.0 onward. Requires the system to have already accumulated at least two records with the `equity_usdc` field in the analyzed period.

---

## Benchmarks and limits

| KPI                | Target                         | Limit          |
|--------------------|--------------------------------|----------------|
| Cumulative P&L     | Positive and growing           | —              |
| Win rate           | > 50% as a reference           | —              |
| Win / loss ratio   | `avg_win_pct` > `avg_loss_pct` | —              |
| Number of trades   | No fixed numerical target      | —              |
| vs buy-and-hold    | Beat BTC's passive return      | Benchmark      |
| Max drawdown       | As low as possible             | **max 15%**    |

The main benchmark is **beating buy-and-hold**: if simply holding BTC would have returned more, the system is not adding value.

---

## Availability since

| KPI                        | Pre-1.27.0 history | From v1.27.0 onward    |
|----------------------------|--------------------|------------------------|
| Cumulative P&L             | ✅                 | ✅                     |
| Win rate                   | ✅                 | ✅                     |
| Average win / average loss | ✅                 | ✅                     |
| Number of trades           | ✅                 | ✅                     |
| Return vs buy-and-hold     | ❌                 | ✅ (after 2+ records)  |
| Max drawdown               | ❌                 | ✅ (after 2+ records)  |

KPIs marked with ❌ for pre-1.27.0 history require the total portfolio value time series (`equity_usdc`), which was not recorded before this version. Past data cannot be retroactively recovered.

---

## 📚 References

- **Computation code**: `src/utils/performance_stats.py`
- **System memory**: `src/utils/memory_manager.py` (`equity_usdc` field)
- **Reviewer prompt**: `config/prompts/performance_reviewer.md`
- **Observability**: `docs/observability.md`
