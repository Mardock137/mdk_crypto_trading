# MDK Crypto Trading

[![CI](https://github.com/Mardock137/mdk_crypto_trading/actions/workflows/ci.yml/badge.svg)](https://github.com/Mardock137/mdk_crypto_trading/actions/workflows/ci.yml)

- **Versione Python**: `3.14.5`
- **Versione MDK Crypto Trading**: `1.32.0`

## 📋 Indice

- [📄 Descrizione](#-descrizione)
- [👥 Agenti e modelli](#-agenti-e-modelli)
- [🔄 Come funziona](#-come-funziona)
- [🚀 Come si lancia](#-come-si-lancia)
- [🤖 API integrate](#-api-integrate)
- [ℹ️ Documentazione](#ℹ️-documentazione)

## 📄 Descrizione

MDK Crypto Trading è un sistema autonomo di trading spot su criptovalute, strutturato come una società di investimenti gestita interamente da agenti IA.

4 agenti operativi collaborano in sequenza (uno analizza il mercato, uno decide l'operazione, uno controlla il rischio e l'ultimo esegue l'ordine su Binance), mentre due agenti consultivi fuori catena alimentano il Decision Maker: uno con un report giornaliero sulle performance, l'altro con un digest news ogni 12 ore. Il sistema gira in loop continuo a intervalli configurabili, opera in modalità DEMO (Binance Demo Trading) o REAL, e registra ogni decisione in log strutturati JSON.

## 👥 Agenti e modelli

| Agente                   | Ruolo                                                                                                      | Modello                    |
|--------------------------|------------------------------------------------------------------------------------------------------------|----------------------------|
| **Market Analyst**       | Analizza indicatori tecnici e genera un segnale di mercato                                                 | GPT-5.6 Terra              |
| **Decision Maker**       | Valuta il segnale e formula una proposta operativa (BUY, SELL, SELL_OCO, HOLD, CANCEL_AND_REPLACE_ORDER)   | Claude Opus 5 (thinking)   |
| **Risk Manager**         | Controlla la proposta, può approvarla, bloccarla o chiedere modifiche                                      | Gemini 3.7 Flash           |
| **Execution Trader**     | Esegue l'ordine approvato su Binance (nessun LLM, puro codice)                                             | —                          |
| **Performance Reviewer** | Ruolo consultivo, fuori catena: genera un report giornaliero letto dal DM                                  | Claude Sonnet 5            |
| **News Reviewer**        | Ruolo consultivo, fuori catena: genera un digest news ogni 12h (sentiment, eventi, risk flag) letto dal DM | Claude Sonnet 5            |

## 🔄 Come funziona

Ogni ciclo operativo segue questa sequenza:

1. Una volta al giorno: il `Performance Reviewer` analizza gli ultimi 7 giorni e genera un report letto dal `Decision Maker` nei cicli successivi
2. Ogni 12 ore: il `News Reviewer` scarica le notizie crypto, ne produce un digest (sentiment BULLISH/BEARISH/NEUTRAL, eventi chiave, risk flag) e lo salva in `data/news_reports/`. Il `Decision Maker` lo legge come contesto nei cicli successivi
3. Raccolta dati di mercato e portafoglio da Binance
4. `Market Analyst` → analisi e segnale
5. `Decision Maker` → proposta operativa (legge il report del Performance Reviewer e il digest news)
6. `Risk Manager` → approvazione o blocco
7. `Execution Trader` → esecuzione su Binance (solo se approvata)
8. Log del ciclo completo in `logs/events/`

L'intervallo tra i cicli è configurabile da `.env` (`CYCLE_INTERVAL_SECONDS`).

Il sistema include tre meccanismi deterministici trasversali al ciclo:

- **Breakeven automatico**: se il P&L non realizzato supera la soglia configurata, lo Stop Loss dell'OCO attivo viene spostato automaticamente al prezzo di ingresso, prima della catena LLM.
- **Cycle-skip**: se prezzo, RSI, segno MACD e ordini aperti sono rimasti invariati rispetto al ciclo precedente (e l'ultima azione era `HOLD`), il ciclo viene saltato senza chiamare alcun agente LLM. Configurabile in `config/cycle_skip.yaml`.
- **Circuit breaker**: dopo 3 errori identici consecutivi il sistema si mette in pausa e invia un alert Telegram, richiedendo riavvio manuale.

## 🚀 Come si lancia

```bash
python -m src.main
```

Per verificare le connessioni API prima di lanciare:

```bash
python dev_support/verify_connections.py
```

## 🤖 API integrate

- **Anthropic API**: Decision Maker (`Claude Opus 5` con adaptive thinking), Performance Reviewer e News Reviewer (`Claude Sonnet 5`)
- **OpenAI API** (`GPT-5.6 Terra`): Market Analyst
- **Gemini API** (`Gemini 3.7 Flash`): Risk Manager
- **Binance API**: dati di mercato, portafoglio, ordini aperti, esecuzione ordini (DEMO e REAL)
- **Alpha Vantage API**: notizie crypto con sentiment score (News Reviewer, opzionale)
- **Telegram Bot API** (opzionale): notifiche in tempo reale su ordini eseguiti, errori e avvio/stop del bot

## ℹ️ Documentazione

- [Struttura della repo](docs/repo_structure.md)
- [Architettura](docs/architecture.md)
- [Configurazione](docs/config.md)
- [Sistema di logging](docs/observability.md)
- [KPI e performance](docs/kpi.md)
- [Endpoints API](docs/api_endpoints.md)
- [Gerarchia e ruoli](docs/hierarchy_and_roles.md)
- [Logica decisionale](docs/decision_logic.md)
- [Deploy su Google Compute Engine](docs/deploy.md)
