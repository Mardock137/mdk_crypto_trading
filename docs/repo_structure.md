# Repo Structure

📁 mdk_crypto_trading/
 │
 ├── 📁 .github/                                             # Configurazione GitHub.
 │    └── 📁 workflows/                                      # Workflow GitHub Actions.
 │         └── 📄 ci.yml                                     # CI: esegue pip-audit (CVE check) e i test pytest automaticamente ad ogni push e pull request.
 │
 ├── 📁 .venv/                                               # Ambiente virtuale con tutte le dipendenze installate.
 │
 ├── 📁 data/                                                # Dati persistenti del sistema (ignorata da git).
 │    ├── 📁 memory/                                         # Memoria decisionale per simbolo (un file JSONL per coppia). Ogni record include i campi operativi del ciclo; dalla v1.27.0 include anche `equity_usdc` (valore totale del portafoglio al momento del ciclo, usato per calcolare i KPI di drawdown e rendimento strategia).
 │    ├── 📁 performance_reports/                            # Report giornalieri del Performance Reviewer (YYYY-MM-DD.md).
 │    └── 📄 heartbeat                                       # Timestamp UTC dell'ultimo ciclo avviato; usato dal HEALTHCHECK Docker.
 │
 ├── 📁 config/                                              # Configurazioni statiche del sistema.
 │    ├── 📁 llm_models/                                     # Configurazione dei modelli IA (model, temperature, max token, ecc.).
 │    │    ├── 📄 decision_maker.yaml                        # Configurazione LLM per il Decision Maker (Claude Opus 4.8).
 │    │    ├── 📄 market_analyst.yaml                        # Configurazione LLM per il Market Analyst (GPT-5.4).
 │    │    ├── 📄 news_reviewer.yaml                          # Configurazione LLM per il News Reviewer (Claude Sonnet 4.6).
 │    │    │    ├── 📄 performance_reviewer.yaml                  # Configurazione LLM per il Performance Reviewer (Claude Sonnet 4.6).
 │    │    └── 📄 risk_manager.yaml                          # Configurazione LLM per il Risk Manager (Gemini 3.1 Pro).
 │    ├── 📁 prompts/                                        # Prompt runtime usati dagli agenti.
 │    │    ├── 📄 decision_maker.md                          # Prompt operativo del Decision Maker.
 │    │    ├── 📄 market_analyst.md                          # Prompt operativo del Market Analyst.
 │    │    ├── 📄 news_reviewer.md                            # Prompt operativo del News Reviewer.
 │    │    │    ├── 📄 performance_reviewer.md                    # Prompt operativo del Performance Reviewer.
 │    │    └── 📄 risk_manager.md                            # Prompt operativo del Risk Manager.
 │    ├── 📄 cycle_skip.yaml                                 # Configurazione del pre-check deterministico che salta cicli quando il contesto e' invariato.
 │    ├── 📄 news.yaml                                       # Configurazione della fonte news (source, topics, tickers, lookback_hours, max_articles, sort).
 │    ├── 📄 symbols.yaml                                    # Simbolo di trading attivo e quote currency (es. BTCUSDC / USDC).
 │    └── 📄 trading.yaml                                    # Regole operative statiche del sistema (min_order_usdc + investment mandate).
 │
 ├── 📁 dev_support/                                         # Materiale di supporto per Chief Mardock e Cursor.
 │    ├── 📁 prompts/                                        # Prompt di progettazione e riferimento.
 │    │    ├── 📄 market_analyst.md
 │    │    ├── 📄 decision_maker.md
 │    │    ├── 📄 risk_manager.md
 │    │    └── 📄 execution_trader.md
 │    ├── 📄 notes.md                                        # Appunti liberi di sviluppo.
 │    ├── 📄 to_do_list.md
 │    ├── 📄 verify_connections.py                           # Script di verifica connessioni API (Binance, OpenAI, Gemini, Claude, Telegram).
 │    └── 📄 whiteboard.md                                   # Lavagna per idee e brainstorming.
 │
 ├── 📁 docs/                                                # Documentazione operativa e tecnica.
 │    ├── 📄 api_endpoints.md                                # Contiene l'elenco degli endpoint API utilizzati.
 │    ├── 📄 architecture.md                                 # Architettura sistema e tech stack.
 │    ├── 📄 config.md                                       # Guida alla configurazione (.env e config/).
 │    ├── 📄 decision_logic.md                               # Descrive la logica decisionale di MDK Crypto Trading.
 │    ├── 📄 deploy.md                                       # Guida completa al deploy su Google Compute Engine con Docker.
 │    ├── 📄 hierarchy_and_roles.md                          # Gerarchia e ruoli dei 4 agenti.
 │    ├── 📄 kpi.md                                          # Definizione ufficiale dei 6 KPI, limiti e benchmark.
 │    ├── 📄 observability.md                                # Sistema di logging: log testuale e log eventi JSON.
 │    ├── 📄 repo_structure.md                               # Struttura e spiegazione della repo.
 │    └── 📄 TEMPLATE.md                                     # Template standard per la documentazione (struttura, emoji, regole).
 │
 ├── 📁 logs/                                                # Log operativi (ignorata da git).
 │    ├── 📁 events/                                         # Log JSON strutturati per ciclo operativo.
 │    │    └── 📄 YYYY-MM-DD.jsonl                           # Un file al giorno, una riga JSON per ciclo.
 │    └── 📄 mdk_crypto_trading.log                          # Log testuale con rotazione automatica (5 MB, 5 backup).
 │
 ├── 📁 src/                                                 # Cartella contenente il codice sorgente di MDK Crypto Trading.
 │    ├── 📁 agents/                                         # Agenti del workflow multi-agente.
 │    │    ├── 📄 base_agent.py                              # Base class minimale (`BaseAgent`) + Template Method per agenti LLM (`BaseLlmAgent`).
 │    │    ├── 📄 decision_maker.py                          # Agente che formula la proposta operativa.
 │    │    ├── 📄 execution_trader.py                        # Agente che esegue la proposta approvata.
 │    │    ├── 📄 market_analyst.py                          # Agente di analisi del mercato.
 │    │    ├── 📄 news_reviewer.py                            # Agente consultivo: digest strutturato del flusso notizie (fuori catena; base del News Reviewer).
 │    │    ├── 📄 performance_reviewer.py                    # Agente consultivo: giudizio giornaliero sulle performance recenti.
 │    │    └── 📄 risk_manager.py                            # Agente di controllo rischio.
 │    ├── 📁 core/                                           # Contratti condivisi e orchestrazione del workflow.
 │    │    ├── 📄 circuit_breaker.py                         # CircuitBreaker: blocca i cicli dopo N errori identici consecutivi (richiede riavvio manuale).
 │    │    ├── 📄 contracts.py                               # Schemi condivisi per input/output degli agenti.
 │    │    ├── 📄 cycle_skip_handler.py                      # CycleSkipHandler: stato cross-cycle e decisione di skip deterministico.
 │    │    ├── 📄 exceptions.py                              # Gerarchia di eccezioni operative: MdkTradingError (base), ExchangeError, LlmError, CycleExecutionError.
 │    │    ├── 📄 notifications.py                           # Funzioni pure che costruiscono i messaggi Telegram (start/stop/error/order).
 │    │    ├── 📄 performance_review_runner.py               # PerformanceReviewRunner: review giornaliero e lettura ultimo report.
 │    │    ├── 📄 position_manager.py                        # PositionManager: calcolo P&L aperto (FIFO), breakeven automatico OCO, flag oco_review_required.
 │    │    ├── 📄 runner.py                                  # Loop operativo ciclico (TradingRunner), direttore d'orchestra.
 │    │    └── 📄 workflow.py                                # Orchestratore della catena di agenti.
 │    ├── 📁 integrations/                                   # Integrazione delle API esterne.
 │    │    ├── 📁 exchange/                                  # Interfaccia verso gli exchange crypto.
 │    │    │    ├── 📄 base_exchange_client.py               # Base interface per i client exchange.
 │    │    │    ├── 📄 binance_client.py                     # Client Binance con supporto DEMO/REAL.
 │    │    │    └── 📄 order_fields.py                       # Costanti dei campi-ordine Binance (fonte unica di verità).
 │    │    ├── 📁 news/                                      # Integrazione fonte notizie crypto.
 │    │    │    ├── 📄 base_news_client.py                   # Interfaccia astratta BaseNewsClient (fonte sostituibile).
 │    │    │    └── 📄 alpha_vantage_client.py               # AlphaVantageClient: download notizie con sentiment + retry tenacity. Base del futuro News Reviewer.
 │    │    └── 📁 llm_interfaces/                            # Interfaccia verso i modelli LLM.
 │    │         ├── 📄 anthropic_interface.py                # Client LLM per Anthropic Claude (con retry automatico).
 │    │         ├── 📄 base_llm_interface.py                 # Base interface per i provider LLM.
 │    │         ├── 📄 gemini_interface.py                   # Client LLM per Google Gemini (con retry automatico).
 │    │         └── 📄 openai_interface.py                   # Client LLM per OpenAI (con retry automatico).
 │    ├── 📁 utils/                                          # Utility comuni e configurazione tecnica.
 │    │    ├── 📄 config.py                                  # Caricamento variabili d'ambiente, YAML e configurazioni.
 │    │    ├── 📄 cycle_skip.py                              # Pre-check deterministico: decide se saltare un ciclo quando il contesto e' invariato.
 │    │    ├── 📄 event_log_reader.py                        # Lettura eventi JSONL recenti usata dal Performance Reviewer.
 │    │    ├── 📄 event_logger.py                            # Logger JSON strutturato per le decisioni di ogni ciclo.
 │    │    ├── 📄 indicators.py                              # Indicatori tecnici (RSI, EMA, SMA, MACD) + `compute_indicators_bundle` (valori correnti + precedenti).
 │    │    ├── 📄 log_utils.py                               # Helper `truncate_for_log`: tronca blob di risposta LLM nei messaggi di WARNING.
 │    │    ├── 📄 logging_config.py                          # Configurazione centralizzata del logging (console + file).
 │    │    ├── 📄 memory_manager.py                          # Persistenza e recupero delle decisioni passate (JSONL) per la memoria del Decision Maker. Cache per-ciclo su letture e calcoli FIFO, invalidata a ogni save_cycle.
 │    │    ├── 📄 performance_stats.py                       # build_performance_stats deterministica + writer del report markdown.
 │    │    └── 📄 telegram_notifier.py                       # Notifiche Telegram opzionali (avvio/stop, ordini eseguiti, errori).
 │    └── 📄 main.py                                         # Entry point del sistema: bootstrap e avvio del runner.
 │
 ├── 📁 tests/                                               # Test automatici per tutte le funzioni e i moduli.
 │    ├── 📁 agents/                                         # Test degli agenti.
 │    │    ├── 📄 test_agent_interfaces.py
 │    │    ├── 📄 test_decision_maker.py
 │    │    ├── 📄 test_execution_trader.py
 │    │    ├── 📄 test_market_analyst.py
 │    │    ├── 📄 test_news_reviewer.py
 │    │    ├── 📄 test_performance_reviewer.py
 │    │    └── 📄 test_risk_manager.py
 │    ├── 📁 core/                                           # Test dei contratti, workflow e runner.
 │    │    ├── 📄 test_contracts.py
 │    │    ├── 📄 test_cycle_skip_handler.py
 │    │    ├── 📄 test_exceptions.py
 │    │    ├── 📄 test_notifications.py
 │    │    ├── 📄 test_performance_review_runner.py
 │    │    ├── 📄 test_position_manager.py
 │    │    ├── 📄 test_runner.py
 │    │    └── 📄 test_workflow.py
 │    ├── 📁 integrations/                                   # Test delle integrazioni.
 │    │    ├── 📁 exchange/
 │    │    │    └── 📄 test_binance_client.py
 │    │    ├── 📁 news/
 │    │    │    └── 📄 test_alpha_vantage_client.py
 │    │    └── 📁 llm_interfaces/
 │    │         ├── 📄 test_anthropic_interface.py
 │    │         ├── 📄 test_base_llm_interface.py
 │    │         ├── 📄 test_openai_interface.py
 │    │         └── 📄 test_gemini_interface.py
 │    ├── 📁 utils/                                          # Test delle utility.
 │    │    ├── 📄 test_config.py
 │    │    ├── 📄 test_cycle_skip.py
 │    │    ├── 📄 test_event_log_reader.py
 │    │    ├── 📄 test_event_logger.py
 │    │    ├── 📄 test_indicators.py
 │    │    ├── 📄 test_logging_config.py
 │    │    ├── 📄 test_memory_manager.py
 │    │    ├── 📄 test_performance_stats.py
 │    │    └── 📄 test_telegram_notifier.py
 │    └── 📄 test_main.py
 │
 ├── 📄 .dockerignore                                        # File e cartelle esclusi dal build context Docker.
 ├── 📄 .env                                                 # Contiene le chiavi API e variabili d'ambiente riservate.
 ├── 📄 .env.example                                         # Contiene un esempio delle variabili d'ambiente in uso.
 ├── 📄 .gitignore                                           # Elenco dei file e delle cartelle esclusi dal controllo di versione.
 ├── 📄 CHANGELOG.md                                         # Storico versioni e modifiche del progetto.
 ├── 📄 docker-compose.yaml                                  # Configurazione Docker Compose per il deploy su GCE.
 ├── 📄 Dockerfile                                           # Immagine Docker per il container di produzione (utente non-root UID 1000, HEALTHCHECK sul file heartbeat).
 ├── 📄 README.md                                            # Panoramica, istruzioni e info rapide sul progetto.
 └── 📄 requirements.txt                                     # Elenco delle dipendenze Python e relative versioni.
