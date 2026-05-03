# Endpoint API

Elenco degli endpoint API esterni utilizzati da MDK Crypto Trading, raggruppati per provider.

---

## 📋 Indice

- [Anthropic](#anthropic)
- [OpenAI](#openai)
- [Gemini](#gemini)
- [Binance](#binance)
- [📚 Riferimenti](#-riferimenti)

---

## Anthropic

- `POST https://api.anthropic.com/v1/messages` → Genera una risposta testuale o JSON strutturato da Claude (Messages API). Usato da `AnthropicInterface` con parametro `system` top-level e supporto `output_config` per JSON schema.

---

## OpenAI

- `POST https://api.openai.com/v1/chat/completions` → Genera una risposta testuale o JSON da GPT (Chat Completions API). Usato da `OpenAiInterface` con supporto per `response_format: json_object`.

---

## Gemini

- `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` → Genera una risposta testuale strutturata da Gemini.

---

## Binance

- `GET https://api.binance.com/api/v3/order` → Mostra i dettagli di un ordine specifico.
- `GET https://api.binance.com/api/v3/exchangeInfo` → Restituisce le informazioni generali dell'exchange e le regole dei simboli.
- `GET https://api.binance.com/api/v3/time` → Restituisce l'ora del server Binance.
- `GET https://api.binance.com/api/v3/account` → Mostra il saldo dell'account Binance.
- `GET https://api.binance.com/api/v3/myTrades?symbol=BTCUSDC` → Mostra lo storico dei trade.
- `GET https://api.binance.com/api/v3/openOrders?symbol=BTCUSDC` → Mostra gli ordini aperti.
- `GET https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDC` → Prezzo attuale del simbolo.
- `GET https://api.binance.com/api/v3/depth?symbol=BTCUSDC&limit=100` → Mostra il livello degli ordini (bid/ask).
- `GET https://api.binance.com/api/v3/trades?symbol=BTCUSDC&limit=50` → Mostra le ultime transazioni avvenute sul mercato.
- `GET https://api.binance.com/api/v3/avgPrice?symbol=BTCUSDC` → Prezzo medio degli ultimi minuti.
- `GET https://api.binance.com/api/v3/klines?symbol=BTCUSDC&interval=1h` → Klines / Candlestick (dati storici).
- `GET https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDC` → Statistiche ultime 24h.

- `POST https://api.binance.com/api/v3/order` → Crea un ordine.
- `POST https://api.binance.com/api/v3/order` (x2) → Per `CANCEL_AND_REPLACE_ORDER`: prima `DELETE /order` per cancellare l'ordine esistente, poi `POST /order` per piazzare il nuovo ordine limit.
- `POST https://api.binance.com/api/v3/order/oco` → Piazza un ordine OCO SELL (`SELL_OCO`): Take Profit LIMIT_MAKER + Stop Loss STOP_LOSS_LIMIT abbinati sulla stessa quantità. Quando uno scatta, l'altro viene cancellato automaticamente da Binance.

- `DELETE https://api.binance.com/api/v3/order` → Cancella un ordine già piazzato.

---

## 📚 Riferimenti

- **Codice**:
  - `src/integrations/llm_interfaces/anthropic_interface.py`
  - `src/integrations/llm_interfaces/openai_interface.py`
  - `src/integrations/llm_interfaces/gemini_interface.py`
  - `src/integrations/exchange/binance_client.py`
- **Doc correlati**: `docs/architecture.md`, `docs/config.md`
- **Risorse esterne**:
  - [Anthropic API](https://docs.anthropic.com/en/api)
  - [OpenAI API](https://platform.openai.com/docs/api-reference)
  - [Gemini API](https://ai.google.dev/api)
  - [Binance API](https://binance-docs.github.io/apidocs/spot/en/)
