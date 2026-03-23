# 📡 Endpoint API

Documentazioni ufficiali:

- [OpenAI API](https://platform.openai.com/docs/api-reference)
- [Gemini API](https://ai.google.dev/api)
- [Binance API](https://binance-docs.github.io/apidocs/spot/en/)

---

## OpenAI

- `POST https://api.openai.com/v1/responses` → Genera una risposta testuale da GPT (Responses API).

## Gemini

- `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` → Genera una risposta testuale strutturata da Gemini.

## Binance

- `GET https://api.binance.com/api/v3/order` → Mostra i dettagli di un ordine specifico.
- `GET https://api.binance.com/api/v3/exchangeInfo` → Restituisce le informazioni generali dell'exchange e le regole dei simboli.
- `GET https://api.binance.com/api/v3/time` → Restituisce l'ora del server Binance.
- `GET https://api.binance.com/api/v3/account` → Mostra il saldo dell'account Binance.
- `GET https://api.binance.com/api/v3/myTrades?symbol=BTCUSDC` → Mostra lo storico dei trade.
- `GET https://api.binance.com/api/v3/openOrders?symbol=BTCUSDC` → Mostra gli ordini aperti.
- `GET https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDC` → Prezzo attuale del simbolo
- `GET https://api.binance.com/api/v3/depth?symbol=ETHUSDT&limit=100` → Mostra il livello degli ordini (bid/ask).
- `GET https://api.binance.com/api/v3/trades?symbol=BTCUSDC&limit=50` → Mostra le ultime transazioni avvenute sul mercato.
- `GET https://api.binance.com/api/v3/avgPrice?symbol=BTCUSDC` → Prezzo medio degli ultimi minuti.
- `GET https://api.binance.com/api/v3/klines?symbol=BTCUSDC&interval=1h` → Klines / Candlestick (dati storici).
- `GET https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDC` → Statistiche ultime 24h.

- `POST https://api.binance.com/api/v3/order` → Crea un ordine.
- `POST https://api.binance.com/api/v3/cancelReplace` → Cancella un ordine già piazzato e lo rimpiazza subito con uno nuovo.

- `DELETE https://api.binance.com/api/v3/order` → Cancella un ordine già piazzato.
