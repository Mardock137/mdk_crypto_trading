# Repo Structure

📁 mdk_crypto_trading/
 │
 ├── 📁 .venv/                                               # Ambiente virtuale con tutte le dipendenze installate.
 │
 ├── 📁 config/                                              # Configurazioni statiche del sistema.
 │    ├── 📁 llm_models/                                     # Configurazione dei modelli IA (model, temperature, max token, ecc.).
 │    │    └── 📄 README.md
 │    ├── 📁 prompts/                                        # Prompt runtime usati dagli agenti.
 │    │    └── 📄 README.md
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
 │    ├── 📄 observability.md                                #
 │    ├── 📄 operational_functions.md                        # Descrive le funzioni operative di MDK Crypto Trading.
 │    └── 📄 repo_structure.md                               # Struttura e spiegazione della repo.
 │
 ├── 📁 logs/
 │
 ├── 📁 src/                                                 # Cartella contenente il codice sorgente di MDK Crypto Trading.
 │    ├── 📁 agents/                                         # Agenti del workflow multi-agente.
 │    │    ├── 📄 base_agent.py                              # Base class comune per tutti gli agenti.
 │    │    ├── 📄 market_analyst.py                          # Agente di analisi del mercato.
 │    │    ├── 📄 decision_maker.py                          # Agente che formula la proposta operativa.
 │    │    ├── 📄 risk_manager.py                            # Agente di controllo rischio.
 │    │    └── 📄 execution_trader.py                        # Agente che esegue la proposta approvata.
 │    ├── 📁 core/                                           # Contratti condivisi e orchestrazione del workflow.
 │    │    ├── 📄 contracts.py                               # Schemi condivisi per input/output degli agenti.
 │    │    └── 📄 workflow.py                                # Orchestratore minimale del ciclo operativo.
 │    ├── 📁 integrations/                                   # Integrazione delle API esterne.
 │    │    ├── 📁 llm_interfaces/                            # Interfaccia verso i modelli LLM.
 │    │    │    ├── 📄 base_llm_interface.py                 # Base interface per i provider LLM.
 │    │    │    ├── 📄 openai_interface.py                   # Client LLM per OpenAI (con retry automatico).
 │    │    │    └── 📄 gemini_interface.py                   # Client LLM per Google Gemini (con retry automatico).
 │    │    └── 📁 exchange/                                  # Interfaccia verso gli exchange crypto.
 │    │         ├── 📄 base_exchange_client.py               # Base interface per i client exchange.
 │    │         └── 📄 binance_client.py                     # Client Binance con supporto DEMO/REAL.
 │    ├── 📁 utils/                                          # Utility comuni e configurazione tecnica.
 │    │    ├── 📄 config.py                                  # Caricamento e validazione delle variabili d'ambiente.
 │    │    └── 📄 logging_config.py                          # Configurazione centralizzata del logging.
 │    └── 📄 main.py                                         #
 │
 ├── 📁 tests/                                               # Test automatici per tutte le funzioni e i moduli.
 │    ├── 📁 agents/                                         # Test delle interfacce degli agenti.
 │    │    └── 📄 test_agent_interfaces.py
 │    ├── 📁 core/                                           # Test dei contratti e del workflow.
 │    │    ├── 📄 test_contracts.py
 │    │    └── 📄 test_workflow.py
 │    ├── 📁 integrations/                                   # Test delle integrazioni.
 │    │    ├── 📁 llm_interfaces/
 │    │    │    ├── 📄 test_base_llm_interface.py
 │    │    │    ├── 📄 test_openai_interface.py
 │    │    │    └── 📄 test_gemini_interface.py
 │    │    └── 📁 exchange/
 │    │         └── 📄 test_binance_client.py
 │    ├── 📁 utils/                                          # Test delle utility.
 │    │    ├── 📄 test_config.py
 │    │    └── 📄 test_logging_config.py
 │    └── 📄 test_main.py
 │
 ├── 📄 .env                                                 # Contiene le chiavi API e variabili d'ambiente riservate.
 ├── 📄 .env.example                                         # Contiene un esempio delle variabili d’ambiente in uso.
 ├── 📄 .gitignore                                           # Elenco dei file e delle cartelle esclusi dal controllo di versione.
 ├── 📄 CHANGELOG.md                                         # Storico versioni e modifiche del progetto.
 ├── 📄 README.md                                            # Panoramica, istruzioni e info rapide sul progetto.
 └── 📄 requirements.txt                                     # Elenco delle dipendenze Python e relative versioni.
