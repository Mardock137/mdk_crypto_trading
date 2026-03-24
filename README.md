# MDK Crypto Trading

- **Versione Python utilizzata**: `3.12.10`
- **Versione MDK Crypto Trading**: `1.0.0`

## 📋 Indice

- [ℹ️ Documentazione](#ℹ️-documentazione)
- [📄 Descrizione](#-descrizione)
- [🤖 API Integrate](#-api-integrate)

## ℹ️ Documentazione

- Per la **struttura della repo** vedi [docs/repo_structure.md](docs/repo_structure.md)
- Per la **configurazione (`config/`)** vedi [docs/config.md](docs/config.md)
- Per l'**architettura** vedi [docs/architecture.md](docs/architecture.md)
- Per la **lista degli endpoints** vedi [docs/api_endpoints.md](docs/api_endpoints.md)
- Per la **logica decisionale** vedi [docs/decision_logic.md](docs/decision_logic.md)
- Per la **lista delle funzioni** vedi [docs/operational_functions.md](docs/operational_functions.md)
- Per il **sistema di logging eventi e metriche** vedi [docs/observability.md](docs/observability.md)

## 📄 Descrizione

MDK Crypto Trading è un sistema multi-agente per il trading spot di criptovalute, pensato per essere strutturato come una vera e propria società di investimenti.
L'MVP separa il workflow in 4 ruoli distinti:

- `Market Analyst`: analizza il mercato e produce un segnale strutturato
- `Decision Maker`: formula una proposta operativa
- `Risk Manager`: approva, blocca o richiede modifiche
- `Execution Trader`: esegue solo proposte approvate

Il flusso operativo dell'MVP e' lineare:
`Market Analyst` -> `Decision Maker` -> `Risk Manager` -> `Execution Trader`

## 🤖 API Integrate

Il progetto integra tre famiglie principali di API:

- **OpenAI API**: usata per le risposte testuali strutturate dei modelli GPT
- **Gemini API**: usata come provider LLM alternativo per analisi e decisioni
- **Binance API**: usata per dati di mercato, stato account, ordini aperti, storico trade ed esecuzione ordini
