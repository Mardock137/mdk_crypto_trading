# API Endpoints

List of external API endpoints used by MDK Crypto Trading, grouped by provider.

---

## 📋 Table of Contents

- [Anthropic](#anthropic)
- [OpenAI](#openai)
- [Gemini](#gemini)
- [Binance](#binance)
- [Alpha Vantage](#alpha-vantage)
- [📚 References](#-references)

---

## Anthropic

- `POST https://api.anthropic.com/v1/messages` → Generates a text response or structured JSON from Claude (Messages API). Used by `AnthropicInterface` with a top-level `system` parameter and `output_config` support for JSON schema.

---

## OpenAI

- `POST https://api.openai.com/v1/chat/completions` → Generates a text or JSON response from GPT (Chat Completions API). Used by `OpenAiInterface` with support for `response_format: json_object`.

---

## Gemini

- `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` → Generates a structured text response from Gemini.

---

## Binance

- `GET https://api.binance.com/api/v3/order` → Shows the details of a specific order.
- `GET https://api.binance.com/api/v3/exchangeInfo` → Returns general exchange information and symbol rules.
- `GET https://api.binance.com/api/v3/time` → Returns the Binance server time.
- `GET https://api.binance.com/api/v3/account` → Shows the Binance account balance.
- `GET https://api.binance.com/api/v3/myTrades?symbol=BTCUSDC` → Shows the trade history.
- `GET https://api.binance.com/api/v3/openOrders?symbol=BTCUSDC` → Shows open orders.
- `GET https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDC` → Current price of the symbol.
- `GET https://api.binance.com/api/v3/depth?symbol=BTCUSDC&limit=100` → Shows the order book depth (bid/ask).
- `GET https://api.binance.com/api/v3/trades?symbol=BTCUSDC&limit=50` → Shows the latest market trades.
- `GET https://api.binance.com/api/v3/avgPrice?symbol=BTCUSDC` → Average price over the last few minutes.
- `GET https://api.binance.com/api/v3/klines?symbol=BTCUSDC&interval=1h` → Klines / Candlestick (historical data).
- `GET https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDC` → Last 24h statistics.

- `POST https://api.binance.com/api/v3/order` → Creates an order.
- `POST https://api.binance.com/api/v3/order` (x2) → For `CANCEL_AND_REPLACE_ORDER`: first `DELETE /order` to cancel the existing order, then `POST /order` to place the new limit order.
- `POST https://api.binance.com/api/v3/orderList/oco` → Places a SELL OCO order (`SELL_OCO`): Take Profit LIMIT_MAKER + Stop Loss STOP_LOSS_LIMIT paired on the same quantity. When one triggers, the other is automatically cancelled by Binance.

- `DELETE https://api.binance.com/api/v3/order` → Cancels an already placed order.

---

## Alpha Vantage

- `GET https://www.alphavantage.co/query?function=NEWS_SENTIMENT` → Downloads crypto news with sentiment score. Used by `AlphaVantageClient` with `topics`, `tickers`, `time_from`, `limit`, `sort` parameters. The `200` response may contain an `Information`, `Note` or `Error Message` field in case of rate limiting or an invalid key: these cases are detected and raised as `NewsError`.

---

## 📚 References

- **Code**:
  - `src/integrations/llm_interfaces/anthropic_interface.py`
  - `src/integrations/llm_interfaces/openai_interface.py`
  - `src/integrations/llm_interfaces/gemini_interface.py`
  - `src/integrations/exchange/binance_client.py`
  - `src/integrations/news/alpha_vantage_client.py`
- **Related docs**: `docs/architecture.md`, `docs/config.md`
- **External resources**:
  - [Anthropic API](https://docs.anthropic.com/en/api)
  - [OpenAI API](https://platform.openai.com/docs/api-reference)
  - [Gemini API](https://ai.google.dev/api)
  - [Binance API](https://binance-docs.github.io/apidocs/spot/en/)
  - [Alpha Vantage API](https://www.alphavantage.co/documentation/)
