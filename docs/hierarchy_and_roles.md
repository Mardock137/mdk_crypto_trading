# 👥 Gerarchia e ruoli

```mermaid
flowchart TD
    marketAnalyst[Market Analyst] --> decisionMaker[Decision Maker]
    decisionMaker --> riskManager[Risk Manager]
    riskManager --> executionTrader[Execution Trader]
```

- `Market Analyst`: analizza il mercato e produce un segnale strutturato.
- `Decision Maker`: trasforma il segnale in una proposta operativa.
- `Risk Manager`: controlla la proposta e puo' approvarla, bloccarla o richiedere modifiche.
- `Execution Trader`: esegue solo proposte approvate.
