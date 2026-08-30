# Repo Structure

📁 mdk_crypto_trading/
 │
 ├── 📁 .github/                                             # GitHub configuration.
 │    └── 📁 workflows/                                      # GitHub Actions workflows.
 │         └── 📄 ci.yml                                     # CI: runs pip-audit (CVE check) and pytest tests automatically on every push and pull request.
 │
 ├── 📁 .venv/                                               # Virtual environment with all dependencies installed.
 │
 ├── 📁 data/                                                # Persistent system data (ignored by git).
 │    ├── 📁 memory/                                         # Decision memory per symbol (one JSONL file per pair). Each record includes the operational fields of the cycle; since v1.27.0 it also includes `equity_usdc` (total portfolio value at the time of the cycle, used to compute drawdown and strategy return KPIs).
 │    ├── 📁 news_reports/                                   # News Reviewer's twice-daily reports (YYYY-MM-DD_HH-MM.md). Produced by NewsReviewRunner every 12h.
 │    ├── 📁 performance_reports/                            # Performance Reviewer's daily reports (YYYY-MM-DD.md).
 │    └── 📄 heartbeat                                       # UTC timestamp of the last cycle started; used by the Docker HEALTHCHECK.
 │
 ├── 📁 config/                                              # Static system configuration.
 │    ├── 📁 llm_models/                                     # AI model configuration (model, temperature, max tokens, etc.).
 │    │    ├── 📄 decision_maker.yaml                        # LLM configuration for the Decision Maker (Claude Opus 5).
 │    │    ├── 📄 market_analyst.yaml                        # LLM configuration for the Market Analyst (GPT-5.6 Terra).
 │    │    ├── 📄 news_reviewer.yaml                         # LLM configuration for the News Reviewer (Claude Sonnet 5).
 │    │    │    ├── 📄 performance_reviewer.yaml             # LLM configuration for the Performance Reviewer (Claude Sonnet 5).
 │    │    └── 📄 risk_manager.yaml                          # LLM configuration for the Risk Manager (Gemini 3.7 Flash).
 │    ├── 📁 prompts/                                        # Runtime prompts used by the agents.
 │    │    ├── 📄 decision_maker.md                          # Operational prompt for the Decision Maker.
 │    │    ├── 📄 market_analyst.md                          # Operational prompt for the Market Analyst.
 │    │    ├── 📄 news_reviewer.md                           # Operational prompt for the News Reviewer.
 │    │    │    ├── 📄 performance_reviewer.md               # Operational prompt for the Performance Reviewer.
 │    │    └── 📄 risk_manager.md                            # Operational prompt for the Risk Manager.
 │    ├── 📄 cycle_skip.yaml                                 # Configuration of the deterministic pre-check that skips cycles when context is unchanged.
 │    ├── 📄 news.yaml                                       # News source configuration (source, topics, tickers, lookback_hours, max_articles, sort).
 │    ├── 📄 symbols.yaml                                    # Active trading symbol and quote currency (e.g. BTCUSDC / USDC).
 │    └── 📄 trading.yaml                                    # Static operational rules of the system (min_order_usdc + investment mandate).
 │
 ├── 📁 dev_support/                                         # Development notes (not versioned).
 │
 ├── 📁 docs/                                                # Operational and technical documentation.
 │    ├── 📄 api_endpoints.md                                # List of API endpoints used.
 │    ├── 📄 architecture.md                                 # System architecture and tech stack.
 │    ├── 📄 config.md                                       # Configuration guide (.env and config/).
 │    ├── 📄 decision_logic.md                               # Describes MDK Crypto Trading's decision logic.
 │    ├── 📄 deploy.md                                       # Complete deployment guide on Google Compute Engine with Docker.
 │    ├── 📄 hierarchy_and_roles.md                          # Hierarchy and roles of the 4 agents.
 │    ├── 📄 kpi.md                                          # Official definition of the 6 KPIs, limits and benchmarks.
 │    ├── 📄 observability.md                                # Logging system: text log and JSON event log.
 │    ├── 📄 repo_structure.md                               # Repo structure and explanation.
 │    └── 📄 TEMPLATE.md                                     # Standard documentation template (structure, emoji, rules).
 │
 ├── 📁 logs/                                                # Operational logs (ignored by git).
 │    ├── 📁 events/                                         # Structured JSON logs per operational cycle.
 │    │    └── 📄 YYYY-MM-DD.jsonl                           # One file per day, one JSON line per cycle.
 │    └── 📄 mdk_crypto_trading.log                          # Text log with automatic rotation (5 MB, 5 backups).
 │
 ├── 📁 src/                                                 # Folder containing the MDK Crypto Trading source code.
 │    ├── 📁 agents/                                         # Multi-agent workflow agents.
 │    │    ├── 📄 base_agent.py                              # Minimal base class (`BaseAgent`) + Template Method for LLM agents (`BaseLlmAgent`).
 │    │    ├── 📄 decision_maker.py                          # Agent that formulates the trade proposal.
 │    │    ├── 📄 execution_trader.py                        # Agent that executes the approved proposal.
 │    │    ├── 📄 market_analyst.py                          # Market analysis agent.
 │    │    ├── 📄 news_reviewer.py                           # Advisory agent: structured digest of the news feed (outside the main chain; invoked by NewsReviewRunner every 12h).
 │    │    ├── 📄 performance_reviewer.py                    # Advisory agent: daily assessment of recent performance.
 │    │    └── 📄 risk_manager.py                            # Risk control agent.
 │    ├── 📁 core/                                           # Shared contracts and workflow orchestration.
 │    │    ├── 📄 circuit_breaker.py                         # CircuitBreaker: blocks cycles after N identical consecutive errors (requires manual restart).
 │    │    ├── 📄 contracts.py                               # Shared schemas for agent input/output.
 │    │    ├── 📄 cycle_skip_handler.py                      # CycleSkipHandler: cross-cycle state and deterministic skip decision.
 │    │    ├── 📄 exceptions.py                              # Operational exception hierarchy: MdkTradingError (base), ExchangeError, LlmError, CycleExecutionError.
 │    │    ├── 📄 news_review_runner.py                      # NewsReviewRunner: news review every 12h with file-based gate, NEUTRAL digest without LLM if no articles, non-blocking.
 │    │    ├── 📄 notifications.py                           # Pure functions that build Telegram messages (start/stop/error/order).
 │    │    ├── 📄 performance_review_runner.py               # PerformanceReviewRunner: daily review and reading of the latest report.
 │    │    ├── 📄 position_manager.py                        # PositionManager: open P&L calculation (FIFO), automatic OCO breakeven, oco_review_required flag.
 │    │    ├── 📄 runner.py                                  # Cyclical operational loop (TradingRunner), the conductor.
 │    │    └── 📄 workflow.py                                # Agent chain orchestrator.
 │    ├── 📁 integrations/                                   # External API integrations.
 │    │    ├── 📁 exchange/                                  # Interface to crypto exchanges.
 │    │    │    ├── 📄 base_exchange_client.py               # Base interface for exchange clients.
 │    │    │    ├── 📄 binance_client.py                     # Binance client with DEMO/REAL support.
 │    │    │    └── 📄 order_fields.py                       # Binance order-field constants (single source of truth).
 │    │    ├── 📁 news/                                      # Crypto news source integration.
 │    │    │    ├── 📄 base_news_client.py                   # Abstract BaseNewsClient interface (replaceable source).
 │    │    │    └── 📄 alpha_vantage_client.py               # AlphaVantageClient: news download with sentiment + tenacity retry. Used by NewsReviewRunner every 12h.
 │    │    └── 📁 llm_interfaces/                            # Interface to LLM models.
 │    │         ├── 📄 anthropic_interface.py                # LLM client for Anthropic Claude (with automatic retry).
 │    │         ├── 📄 base_llm_interface.py                 # Base interface for LLM providers.
 │    │         ├── 📄 gemini_interface.py                   # LLM client for Google Gemini (with automatic retry).
 │    │         └── 📄 openai_interface.py                   # LLM client for OpenAI (with automatic retry).
 │    ├── 📁 utils/                                          # Common utilities and technical configuration.
 │    │    ├── 📄 config.py                                  # Loading of environment variables, YAML and configurations.
 │    │    ├── 📄 cycle_skip.py                              # Deterministic pre-check: decides whether to skip a cycle when context is unchanged.
 │    │    ├── 📄 event_log_reader.py                        # Reads recent JSONL events, used by the Performance Reviewer.
 │    │    ├── 📄 event_logger.py                            # Structured JSON logger for each cycle's decisions.
 │    │    ├── 📄 indicators.py                              # Technical indicators (RSI, EMA, SMA, MACD) + `compute_indicators_bundle` (current + previous values).
 │    │    ├── 📄 log_utils.py                               # `truncate_for_log` helper: truncates LLM response blobs in WARNING log messages.
 │    │    ├── 📄 logging_config.py                          # Centralized logging configuration (console + file).
 │    │    ├── 📄 memory_manager.py                          # Persistence and retrieval of past decisions (JSONL) for the Decision Maker's memory. Per-cycle cache for reads and FIFO calculations, invalidated on every save_cycle.
 │    │    ├── 📄 news_report.py                             # write_news_report: serializes a NewsDigest to markdown (YYYY-MM-DD_HH-MM.md) and saves it in data/news_reports/.
 │    │    ├── 📄 performance_stats.py                       # Deterministic build_performance_stats + markdown report writer.
 │    │    └── 📄 telegram_notifier.py                       # Optional Telegram notifications (start/stop, executed orders, errors).
 │    └── 📄 main.py                                         # System entry point: bootstrap and runner startup.
 │
 ├── 📁 tests/                                               # Automated tests for all functions and modules.
 │    ├── 📁 agents/                                         # Agent tests.
 │    │    ├── 📄 test_agent_interfaces.py
 │    │    ├── 📄 test_decision_maker.py
 │    │    ├── 📄 test_execution_trader.py
 │    │    ├── 📄 test_market_analyst.py
 │    │    ├── 📄 test_news_reviewer.py
 │    │    ├── 📄 test_performance_reviewer.py
 │    │    └── 📄 test_risk_manager.py
 │    ├── 📁 core/                                           # Contract, workflow and runner tests.
 │    │    ├── 📄 test_contracts.py
 │    │    ├── 📄 test_cycle_skip_handler.py
 │    │    ├── 📄 test_exceptions.py
 │    │    ├── 📄 test_news_review_runner.py
 │    │    ├── 📄 test_notifications.py
 │    │    ├── 📄 test_performance_review_runner.py
 │    │    ├── 📄 test_position_manager.py
 │    │    ├── 📄 test_runner.py
 │    │    └── 📄 test_workflow.py
 │    ├── 📁 integrations/                                   # Integration tests.
 │    │    ├── 📁 exchange/
 │    │    │    └── 📄 test_binance_client.py
 │    │    ├── 📁 news/
 │    │    │    └── 📄 test_alpha_vantage_client.py
 │    │    └── 📁 llm_interfaces/
 │    │         ├── 📄 test_anthropic_interface.py
 │    │         ├── 📄 test_base_llm_interface.py
 │    │         ├── 📄 test_openai_interface.py
 │    │         └── 📄 test_gemini_interface.py
 │    ├── 📁 utils/                                          # Utility tests.
 │    │    ├── 📄 test_config.py
 │    │    ├── 📄 test_cycle_skip.py
 │    │    ├── 📄 test_event_log_reader.py
 │    │    ├── 📄 test_event_logger.py
 │    │    ├── 📄 test_indicators.py
 │    │    ├── 📄 test_logging_config.py
 │    │    ├── 📄 test_memory_manager.py
 │    │    ├── 📄 test_news_report.py
 │    │    ├── 📄 test_performance_stats.py
 │    │    └── 📄 test_telegram_notifier.py
 │    └── 📄 test_main.py
 │
 ├── 📄 .dockerignore                                        # Files and folders excluded from the Docker build context.
 ├── 📄 .env                                                 # Contains API keys and confidential environment variables.
 ├── 📄 .env.example                                         # Contains an example of the environment variables in use.
 ├── 📄 .gitignore                                           # List of files and folders excluded from version control.
 ├── 📄 CHANGELOG.md                                         # Version history and project changes.
 ├── 📄 docker-compose.yaml                                  # Docker Compose configuration for GCE deployment.
 ├── 📄 Dockerfile                                           # Docker image for the production container (non-root user UID 1000, HEALTHCHECK on the heartbeat file).
 ├── 📄 LICENSE                                              # MIT license.
 ├── 📄 README.md                                            # Overview, instructions and quick project info.
 ├── 📄 requirements.txt                                     # List of Python dependencies and their versions.
 └── 📄 verify_connections.py                                # Diagnostic script that tests all external API connections (Binance, OpenAI, Gemini, Claude, Telegram, Alpha Vantage).
