# MDK Crypto Trading

- **Python**: `3.12.10`
- **Versione**: `1.4.3`

## 📋 Indice

- [📄 Descrizione](#-descrizione)
- [👥 Agenti e modelli](#-agenti-e-modelli)
- [🔄 Come funziona](#-come-funziona)
- [🚀 Come si lancia](#-come-si-lancia)
- [🤖 API integrate](#-api-integrate)
- [ℹ️ Documentazione](#ℹ️-documentazione)

## 📄 Descrizione

MDK Crypto Trading è un sistema autonomo di trading spot su criptovalute, strutturato come una società di investimenti gestita interamente da agenti IA.

4 agenti collaborano in sequenza: uno analizza il mercato, uno decide l'operazione, uno controlla il rischio e l'ultimo esegue l'ordine su Binance. Il sistema gira in loop continuo a intervalli configurabili, opera in modalità DEMO (Binance Demo Trading) o REAL, e registra ogni decisione in log strutturati JSON.

## 👥 Agenti e modelli

| Agente               | Ruolo                                                                 | Modello           |
|----------------------|-----------------------------------------------------------------------|-------------------|
| **Market Analyst**   | Analizza indicatori tecnici e genera un segnale di mercato            | Claude Sonnet 4.6 |
| **Decision Maker**   | Valuta il segnale e formula una proposta operativa (BUY, SELL, HOLD)  | GPT-5.4           |
| **Risk Manager**     | Controlla la proposta, può approvarla, bloccarla o chiedere modifiche | Gemini 3.1 Pro    |
| **Execution Trader** | Esegue l'ordine approvato su Binance (nessun LLM, puro codice)        | —                 |

## 🔄 Come funziona

Ogni ciclo operativo segue questa sequenza:

1. Raccolta dati di mercato e portafoglio da Binance
2. `Market Analyst` → analisi e segnale
3. `Decision Maker` → proposta operativa
4. `Risk Manager` → approvazione o blocco
5. `Execution Trader` → esecuzione su Binance (solo se approvata)
6. Log del ciclo completo in `logs/events/`

L'intervallo tra i cicli è configurabile da `.env` (`CYCLE_INTERVAL_SECONDS`).

## 🚀 Come si lancia

```bash
python -m src.main
```

Per verificare le connessioni API prima di lanciare:

```bash
python dev_support/verify_connections.py
```

## 🤖 API integrate

- **Anthropic API** (`Claude Sonnet 4.6`): Market Analyst
- **OpenAI API** (`GPT-5.4`): Decision Maker
- **Gemini API** (`Gemini 3.1 Pro`): Risk Manager
- **Binance API**: dati di mercato, portafoglio, ordini aperti, esecuzione ordini (DEMO e REAL)
- **Telegram Bot API** (opzionale): notifiche in tempo reale su ordini eseguiti, errori e avvio/stop del bot

## ℹ️ Documentazione

- [Struttura della repo](docs/repo_structure.md)
- [Architettura](docs/architecture.md)
- [Configurazione](docs/config.md)
- [Sistema di logging](docs/observability.md)
- [Endpoints API](docs/api_endpoints.md)
- [Gerarchia e ruoli](docs/hierarchy_and_roles.md)
- [Logica decisionale](docs/decision_logic.md)
- [Deploy su Google Compute Engine](docs/deploy.md)
