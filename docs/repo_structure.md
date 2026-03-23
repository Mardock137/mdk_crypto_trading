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
 │    ├── 📄 notes.md
 │    ├── 📁 prompts/                                        # Prompt di progettazione e riferimento umano per gli agenti.
 │    │    ├── 📄 market_analyst.md
 │    │    ├── 📄 decision_maker.md
 │    │    ├── 📄 risk_manager.md
 │    │    └── 📄 execution_trader.md
 │    ├── 📄 to_do_list.md
 │    └── 📄 whiteboard.md
 │
 ├── 📁 docs/                                                # Documentazione operativa e tecnica.
 │    ├── 📄 api_endpoints.md                                # Contiene l'elenco degli endpoint API utilizzati.
 │    ├── 📄 architecture.md                                 # Architettura sistema e tech stack.
 │    ├── 📄 config.md                                       #
 │    ├── 📄 decision_logic.md                               # Descrive la logica decisionale di MDK Crypto Trading.
 │    ├── 📄 observability.md                                #
 │    ├── 📄 operational_functions.md                        # Descrive le funzioni operative di MDK Crypto Trading.
 │    └── 📄 repo_structure.md                               # Struttura e spiegazione della repo.
 │
 ├── 📁 logs/
 │
 ├── 📁 src/                                                 # Cartella contenente il codice sorgente di MDK Crypto Trading.
 │    ├── 📄 __init__.py
 │    ├── 📁 agents/                                         # Agenti del workflow multi-agente.
 │    │    ├── 📄 __init__.py
 │    │    ├── 📄 base_agent.py                              # Base class comune per tutti gli agenti.
 │    │    ├── 📄 market_analyst.py                          # Agente di analisi del mercato.
 │    │    ├── 📄 decision_maker.py                          # Agente che formula la proposta operativa.
 │    │    ├── 📄 risk_manager.py                            # Agente di controllo rischio.
 │    │    └── 📄 execution_trader.py                        # Agente che esegue la proposta approvata.
 │    ├── 📁 core/                                           # Contratti condivisi e orchestrazione del workflow.
 │    │    ├── 📄 __init__.py
 │    │    ├── 📄 contracts.py                               # Schemi condivisi per input/output degli agenti.
 │    │    └── 📄 workflow.py                                # Orchestratore minimale del ciclo operativo.
 │    ├── 📁 integrations/                                   # Integrazione delle API esterne.
 │    │    ├── 📄 __init__.py
 │    │    └── 📁 llm_interfaces/                            # Interfaccia verso i modelli LLM.
 │    │         ├── 📄 __init__.py
 │    │         └── 📄 base_llm_interface.py                 # Base interface per i provider LLM.
 │    └── 📁 utils/                                          # Utility comuni e configurazione tecnica.
 │         ├── 📄 __init__.py
 │         ├── 📄 config.py                                  # Caricamento e validazione delle variabili d'ambiente.
 │         └── 📄 logging_config.py                          # Configurazione centralizzata del logging.
 │
 ├── 📁 tests/                                               # Test automatici per tutte le funzioni e i moduli.
 │    ├── 📄 __init__.py
 │    ├── 📁 agents/                                         # Test delle interfacce degli agenti.
 │    │    ├── 📄 __init__.py
 │    │    └── 📄 test_agent_interfaces.py
 │    ├── 📁 core/                                           # Test dei contratti e del workflow.
 │    │    ├── 📄 __init__.py
 │    │    ├── 📄 test_contracts.py
 │    │    └── 📄 test_workflow.py
 │    ├── 📁 integrations/                                   # Test delle integrazioni.
 │    │    ├── 📄 __init__.py
 │    │    └── 📁 llm_interfaces/
 │    │         ├── 📄 __init__.py
 │    │         └── 📄 test_base_llm_interface.py
 │    └── 📁 utils/                                          # Test delle utility.
 │         ├── 📄 __init__.py
 │         ├── 📄 test_config.py
 │         └── 📄 test_logging_config.py
 │
 ├── 📄 .env                                                 # Contiene le chiavi API e variabili d'ambiente riservate.
 ├── 📄 .env.example                                         # Contiene un esempio delle variabili d’ambiente in uso.
 ├── 📄 .gitignore                                           # Elenco dei file e delle cartelle esclusi dal controllo di versione.
 ├── 📄 CHANGELOG.md                                         # Storico versioni e modifiche del progetto.
 ├── 📄 README.md                                            # Panoramica, istruzioni e info rapide sul progetto.
 └── 📄 requirements.txt                                     # Elenco delle dipendenze Python e relative versioni.
