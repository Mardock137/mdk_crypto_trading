# Repo Structure

📁 mdk_crypto_trading/
 │
 ├── 📁 .venv/                                               # Ambiente virtuale con tutte le dipendenze installate.
 │
 ├── 📁 config/                                              # Configurazioni statiche del sistema.
 │    ├── 📁 llm_models/                                     # Configurazione dei modelli IA (model, temperature, max token, ecc.).
 │    │    ├── 📄 decision_maker.yaml                        # Configurazione LLM per il Decision Maker (GPT-5.4).
 │    │    ├── 📄 market_analyst.yaml                        # Configurazione LLM per il Market Analyst (GPT-5.4).
 │    │    ├── 📄 README.md
 │    │    └── 📄 risk_manager.yaml                          # Configurazione LLM per il Risk Manager (Gemini 3.1 Pro).
 │    ├── 📁 prompts/                                        # Prompt runtime usati dagli agenti.
 │    │    ├── 📄 decision_maker.md                          # Prompt operativo del Decision Maker.
 │    │    ├── 📄 market_analyst.md                          # Prompt operativo del Market Analyst.
 │    │    ├── 📄 README.md
 │    │    └── 📄 risk_manager.md                            # Prompt operativo del Risk Manager.
 │    ├── 📄 symbols.yaml                                    # Simbolo di trading attivo (es. BTCUSDC).
 │    └── 📄 trading.yaml                                    # Regole operative statiche del sistema (es. min_order_usdc).
 │
 ├── 📁 dev_support/                                         # Materiale di supporto per Chief Mardock e Cursor.
 │    ├── 📁 prompts/                                        # Prompt di progettazione e riferimento umano per gli agenti.
 │    │    ├── 📄 market_analyst.md
 │    │    ├── 📄 decision_maker.md
 │    │    ├── 📄 risk_manager.md
 │    │    └── 📄 execution_trader.md
 │    ├── 📄 notes.md
 │    ├── 📄 to_do_list.md
 │    └── 📄 whiteboard.md
 │
 ├── 📁 docs/                                                # Documentazione operativa e tecnica.
 │    ├── 📄 api_endpoints.md                                # Contiene l'elenco degli endpoint API utilizzati.
 │    ├── 📄 architecture.md                                 # Architettura sistema e tech stack.
 │    ├── 📄 config.md                                       #
 │    ├── 📄 decision_logic.md                               # Descrive la logica decisionale di MDK Crypto Trading.
 │    ├── 📄 hierarchy_and_roles.md                          #
 │    ├── 📄 observability.md                                # Sistema di logging: log testuale e log eventi JSON.
 │    ├── 📄 operational_functions.md                        # Descrive le funzioni operative di MDK Crypto Trading.
 │    └── 📄 repo_structure.md                               # Struttura e spiegazione della repo.
 │
 ├── 📁 logs/                                                # Log operativi (ignorata da git).
 │    ├── 📄 mdk_crypto_trading.log                          # Log testuale con rotazione automatica (5 MB, 5 backup).
 │    └── 📁 events/                                         # Log JSON strutturati per ciclo operativo.
 │         └── 📄 YYYY-MM-DD.jsonl                           # Un file al giorno, una riga JSON per ciclo.
 │
 ├── 📁 src/                                                 # Cartella contenente il codice sorgente di MDK Crypto Trading.
 │    ├── 📁 agents/                                         # Agenti del workflow multi-agente.
 │    │    ├── 📄 base_agent.py                              # Base class comune per tutti gli agenti.
 │    │    ├── 📄 decision_maker.py                          # Agente che formula la proposta operativa.
 │    │    ├── 📄 execution_trader.py                        # Agente che esegue la proposta approvata.
 │    │    ├── 📄 market_analyst.py                          # Agente di analisi del mercato.
 │    │    └── 📄 risk_manager.py                            # Agente di controllo rischio.
 │    ├── 📁 core/                                           # Contratti condivisi e orchestrazione del workflow.
 │    │    ├── 📄 contracts.py                               # Schemi condivisi per input/output degli agenti.
 │    │    ├── 📄 runner.py                                  # Loop operativo ciclico (TradingRunner).
 │    │    └── 📄 workflow.py                                # Orchestratore della catena di agenti.
 │    ├── 📁 integrations/                                   # Integrazione delle API esterne.
 │    │    ├── 📁 exchange/                                  # Interfaccia verso gli exchange crypto.
 │    │    │    ├── 📄 base_exchange_client.py               # Base interface per i client exchange.
 │    │    │    └── 📄 binance_client.py                     # Client Binance con supporto DEMO/REAL.
 │    │    └── 📁 llm_interfaces/                            # Interfaccia verso i modelli LLM.
 │    │         ├── 📄 base_llm_interface.py                 # Base interface per i provider LLM.
 │    │         ├── 📄 gemini_interface.py                   # Client LLM per Google Gemini (con retry automatico).
 │    │         └── 📄 openai_interface.py                   # Client LLM per OpenAI (con retry automatico).
 │    ├── 📁 utils/                                          # Utility comuni e configurazione tecnica.
 │    │    ├── 📄 config.py                                  # Caricamento variabili d'ambiente, YAML e configurazioni.
 │    │    ├── 📄 event_logger.py                            # Logger JSON strutturato per le decisioni di ogni ciclo.
 │    │    ├── 📄 indicators.py                              # Indicatori tecnici: RSI, EMA, SMA, MACD.
 │    │    └── 📄 logging_config.py                          # Configurazione centralizzata del logging (console + file).
 │    └── 📄 main.py                                         # Entry point del sistema: bootstrap e avvio del runner.
 │
 ├── 📁 tests/                                               # Test automatici per tutte le funzioni e i moduli.
 │    ├── 📁 agents/                                         # Test degli agenti.
 │    │    ├── 📄 test_agent_interfaces.py
 │    │    ├── 📄 test_decision_maker.py
 │    │    ├── 📄 test_execution_trader.py
 │    │    ├── 📄 test_market_analyst.py
 │    │    └── 📄 test_risk_manager.py
 │    ├── 📁 core/                                           # Test dei contratti, workflow e runner.
 │    │    ├── 📄 test_contracts.py
 │    │    ├── 📄 test_runner.py
 │    │    └── 📄 test_workflow.py
 │    ├── 📁 integrations/                                   # Test delle integrazioni.
 │    │    ├── 📁 exchange/
 │    │    │    └── 📄 test_binance_client.py
 │    │    └── 📁 llm_interfaces/
 │    │         ├── 📄 test_base_llm_interface.py
 │    │         ├── 📄 test_openai_interface.py
 │    │         └── 📄 test_gemini_interface.py
 │    ├── 📁 utils/                                          # Test delle utility.
 │    │    ├── 📄 test_config.py
 │    │    ├── 📄 test_event_logger.py
 │    │    ├── 📄 test_indicators.py
 │    │    └── 📄 test_logging_config.py
 │    └── 📄 test_main.py
 │
 ├── 📄 .env                                                 # Contiene le chiavi API e variabili d'ambiente riservate.
 ├── 📄 .env.example                                         # Contiene un esempio delle variabili d’ambiente in uso.
 ├── 📄 .gitignore                                           # Elenco dei file e delle cartelle esclusi dal controllo di versione.
 ├── 📄 CHANGELOG.md                                         # Storico versioni e modifiche del progetto.
 ├── 📄 README.md                                            # Panoramica, istruzioni e info rapide sul progetto.
 └── 📄 requirements.txt                                     # Elenco delle dipendenze Python e relative versioni.
