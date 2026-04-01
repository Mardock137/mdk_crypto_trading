<!-- markdownlint-disable -->
# 📋 Changelog

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
