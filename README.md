# MDK Crypto Trading

[![CI](https://github.com/Mardock137/mdk_crypto_trading/actions/workflows/ci.yml/badge.svg)](https://github.com/Mardock137/mdk_crypto_trading/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

- **MDK Crypto Trading version**: `1.32.2`
- **License**: [MIT](LICENSE)

## 📋 Table of Contents

- [📄 Description](#-description)
- [👥 Agents and models](#-agents-and-models)
- [🔄 How it works](#-how-it-works)
- [🧰 Tech stack](#-tech-stack)
- [🚀 Setup and run](#-setup-and-run)
- [🤖 Integrated APIs](#-integrated-apis)
- [⚠️ Notes and disclaimer](#️-notes-and-disclaimer)
- [ℹ️ Documentation](#ℹ️-documentation)

## 📄 Description

MDK Crypto Trading is an autonomous spot trading system for cryptocurrencies, structured as an investment firm run entirely by AI agents.

4 operational agents collaborate in sequence (one analyzes the market, one decides the trade, one checks the risk, and the last one executes the order on Binance), while two advisory agents outside the main chain feed the Decision Maker: one with a daily performance report, the other with a news digest every 12 hours. The system runs in a continuous loop at configurable intervals, operates in DEMO mode (Binance Demo Trading) or REAL mode, and logs every decision in structured JSON logs.

## 👥 Agents and models

| Agent                    | Role                                                                                                                        | Model                    |
|--------------------------|-----------------------------------------------------------------------------------------------------------------------------|--------------------------|
| **Market Analyst**       | Analyzes technical indicators and generates a market signal                                                                 | GPT-5.6 Terra            |
| **Decision Maker**       | Evaluates the signal and formulates a trade proposal (BUY, SELL, SELL_OCO, HOLD, CANCEL_AND_REPLACE_ORDER)                  | Claude Opus 5 (thinking) |
| **Risk Manager**         | Reviews the proposal, can approve it, block it, or request changes                                                          | Gemini 3.7 Flash         |
| **Execution Trader**     | Executes the approved order on Binance (no LLM, pure code)                                                                  | —                        |
| **Performance Reviewer** | Advisory role, outside the main chain: generates a daily report read by the DM                                              | Claude Sonnet 5          |
| **News Reviewer**        | Advisory role, outside the main chain: generates a news digest every 12h (sentiment, key events, risk flags) read by the DM | Claude Sonnet 5          |

## 🔄 How it works

Every operational cycle follows this sequence:

1. Once a day: the `Performance Reviewer` analyzes the last 7 days and generates a report read by the `Decision Maker` in the following cycles
2. Every 12 hours: the `News Reviewer` fetches crypto news, produces a digest (sentiment BULLISH/BEARISH/NEUTRAL, key events, risk flags) and saves it in `data/news_reports/`. The `Decision Maker` reads it as context in the following cycles
3. Market and portfolio data collection from Binance
4. `Market Analyst` → analysis and signal
5. `Decision Maker` → trade proposal (reads the Performance Reviewer's report and the news digest)
6. `Risk Manager` → approval or block
7. `Execution Trader` → execution on Binance (only if approved)
8. Full cycle logging in `logs/events/`

The interval between cycles is configurable via `.env` (`CYCLE_INTERVAL_SECONDS`).

The system includes three deterministic mechanisms that run across every cycle:

- **Automatic breakeven**: if the unrealized P&L exceeds the configured threshold, the Stop Loss of the active OCO order is automatically moved to the entry price, before the LLM chain runs.
- **Cycle-skip**: if price, RSI, MACD sign and open orders are unchanged from the previous cycle (and the last action was `HOLD`), the cycle is skipped without calling any LLM agent. Configurable in `config/cycle_skip.yaml`.
- **Circuit breaker**: after 3 identical consecutive errors, the system pauses and sends a Telegram alert, requiring a manual restart.

## 🧰 Tech stack

- **Language**: Python 3.14
- **LLM providers**: Anthropic (Claude), OpenAI (GPT), Google (Gemini)
- **Exchange**: Binance (`python-binance`)
- **Data and configuration**: pandas, numpy, PyYAML, python-dotenv
- **Resilience and networking**: tenacity (automatic retry), requests
- **Testing**: pytest
- **CI/CD**: GitHub Actions (lint, `pip-audit` for CVE checks, automated tests)
- **Containerization**: Docker, Docker Compose
- **Deployment**: Google Compute Engine

## 🚀 Setup and run

### Requirements

- Python 3.14+
- Active API keys for: Binance (or Binance Demo Trading), Anthropic, OpenAI, Google Gemini
- Optional API keys for: Alpha Vantage (news), Telegram Bot (notifications)

### Installation

```bash
git clone https://github.com/Mardock137/mdk_crypto_trading.git
cd mdk_crypto_trading
pip install -r requirements.txt
```

### Configuration

Copy the example file and fill in your API keys:

```bash
cp .env.example .env
```

### Run

```bash
python -m src.main
```

To verify API connections before launching:

```bash
python verify_connections.py
```

## 🤖 Integrated APIs

- **Anthropic API**: Decision Maker (`Claude Opus 5` with adaptive thinking), Performance Reviewer and News Reviewer (`Claude Sonnet 5`)
- **OpenAI API** (`GPT-5.6 Terra`): Market Analyst
- **Gemini API** (`Gemini 3.7 Flash`): Risk Manager
- **Binance API**: market data, portfolio, open orders, order execution (DEMO and REAL)
- **Alpha Vantage API**: crypto news with sentiment score (News Reviewer, optional)
- **Telegram Bot API** (optional): real-time notifications on executed orders, errors, and bot start/stop

## ⚠️ Notes and disclaimer

This project was built for educational and demonstration purposes, to explore AI agent orchestration applied to a real-world use case: algorithmic trading. It does not constitute financial advice. Running it in `REAL` mode executes orders with real funds and carries the risk of capital loss: it is used entirely at the operator's own risk.

## ℹ️ Documentation

- [Repo structure](docs/repo_structure.md)
- [Architecture](docs/architecture.md)
- [Configuration](docs/config.md)
- [Logging system](docs/observability.md)
- [KPIs and performance](docs/kpi.md)
- [API endpoints](docs/api_endpoints.md)
- [Hierarchy and roles](docs/hierarchy_and_roles.md)
- [Decision logic](docs/decision_logic.md)
- [Deploy on Google Compute Engine](docs/deploy.md)
