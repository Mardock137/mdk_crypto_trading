"""
Script di verifica connessioni API.

Testa in sequenza: Binance Demo (ping, mercato, portafoglio), OpenAI, Gemini, Claude,
Telegram e Alpha Vantage. Ogni test e' indipendente: se uno fallisce gli altri continuano.

Utilizzo:
    python verify_connections.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Aggiunge la root del progetto al path per importare src/
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.integrations.exchange.binance_client import BinanceClient
from src.integrations.llm_interfaces.anthropic_interface import AnthropicInterface
from src.integrations.llm_interfaces.gemini_interface import GeminiInterface
from src.integrations.llm_interfaces.openai_interface import OpenAiInterface
from src.integrations.news.alpha_vantage_client import AlphaVantageClient
from src.utils.config import load_news_config, load_settings
from src.utils.logging_config import configure_logging
from src.utils.telegram_notifier import TelegramNotifier


def _ok(msg: str) -> None:
    print(f"  ✓  {msg}")


def _err(label: str, exc: Exception) -> None:
    print(f"  ✗  {label}: {exc}")


def _header(title: str) -> None:
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")


def test_binance_ping(client: BinanceClient) -> None:
    _header("1. Binance Demo — Ping")
    try:
        client.ping()
        _ok("Connessione riuscita")
    except Exception as exc:
        _err("Ping fallito", exc)


def test_binance_market(client: BinanceClient) -> None:
    _header("2. Binance Demo — Dati di mercato")
    try:
        snapshot = client.get_market_snapshot("BTCUSDC")
        _ok(f"Prezzo BTCUSDC: {snapshot.price}")
        _ok(f"RSI-14:         {snapshot.indicators.get('rsi_14')}")
        _ok(f"MACD:           {snapshot.indicators.get('macd')}")
        _ok(f"Volume 24h:     {snapshot.volume_24h}")
    except Exception as exc:
        _err("Dati di mercato falliti", exc)


def test_binance_portfolio(client: BinanceClient) -> None:
    _header("3. Binance Demo — Portafoglio")
    try:
        state = client.get_portfolio_state("BTCUSDC")
        _ok(f"USDC disponibile: {state.usdc_balance:.2f}")
        _ok(f"BTC disponibile:  {state.portfolio_qty_free}")
        _ok(f"Snapshot:         {state.portfolio_snapshot}")
    except Exception as exc:
        _err("Portafoglio fallito", exc)


_PING_SYSTEM_PROMPT = (
    'Rispondi esclusivamente con un JSON valido nel formato {"status": "OK"}, '
    "senza testo aggiuntivo."
)
_PING_USER_PAYLOAD = {"instruction": "Conferma che sei operativo."}


def test_openai(api_key: str | None) -> None:
    _header("4. OpenAI — Risposta base")
    if not api_key:
        print("  —  OPENAI_API_KEY non configurata, test saltato.")
        return
    try:
        llm = OpenAiInterface(api_key=api_key, model="gpt-4o-mini")
        response = llm.generate_json(_PING_SYSTEM_PROMPT, _PING_USER_PAYLOAD)
        _ok(f"Risposta: {response}")
    except Exception as exc:
        _err("OpenAI fallito", exc)


def test_gemini(api_key: str | None) -> None:
    _header("5. Gemini — Risposta base")
    if not api_key:
        print("  —  GEMINI_API_KEY non configurata, test saltato.")
        return
    try:
        llm = GeminiInterface(api_key=api_key, model="gemini-3.1-flash-lite-preview")
        response = llm.generate_json(_PING_SYSTEM_PROMPT, _PING_USER_PAYLOAD)
        _ok(f"Risposta: {response}")
    except Exception as exc:
        _err("Gemini fallito", exc)


def test_claude(api_key: str | None) -> None:
    _header("6. Claude — Risposta base")
    if not api_key:
        print("  —  CLAUDE_API_KEY non configurata, test saltato.")
        return
    try:
        llm = AnthropicInterface(
            api_key=api_key,
            model="claude-sonnet-4-6",
            max_tokens=64,
        )
        response = llm.generate_json(_PING_SYSTEM_PROMPT, _PING_USER_PAYLOAD)
        _ok(f"Risposta: {response}")
    except Exception as exc:
        _err("Claude fallito", exc)


def test_alpha_vantage(api_key: str | None) -> None:
    _header("8. Alpha Vantage — Notizie crypto")
    if not api_key:
        print("  —  ALPHA_VANTAGE_API_KEY non configurata, test saltato.")
        return
    try:
        news_config = load_news_config()
        query = news_config.get("query", {})
        client = AlphaVantageClient(
            api_key=api_key,
            topics=str(query.get("topics", "blockchain")),
            tickers=str(query.get("tickers", "")),
            lookback_hours=int(query.get("lookback_hours", 12)),
            max_articles=int(query.get("max_articles", 50)),
            sort=str(query.get("sort", "LATEST")),
        )
        articles = client.get_recent_news()
        _ok(f"Articoli ricevuti: {len(articles)}")
        if articles:
            _ok(f"Primo titolo: {articles[0].title[:80]}")
    except Exception as exc:
        _err("Alpha Vantage fallito", exc)


def test_telegram(bot_token: str | None, chat_id: str | None) -> None:
    _header("7. Telegram — Notifica di test")
    if not bot_token or not chat_id:
        print("  —  TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID non configurati, test saltato.")
        return
    try:
        notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
        notifier.send_message("✅ <b>MDK Crypto Trading</b>\nNotifiche Telegram attive e funzionanti.")
        _ok("Messaggio inviato con successo")
    except Exception as exc:
        _err("Telegram fallito", exc)


def main() -> None:
    print("\n🔌 MDK Crypto Trading — Verifica connessioni API")

    settings = load_settings()
    configure_logging(level=settings.log_level)
    binance_client = BinanceClient(settings)

    test_binance_ping(binance_client)
    test_binance_market(binance_client)
    test_binance_portfolio(binance_client)
    test_openai(settings.openai_api_key)
    test_gemini(settings.gemini_api_key)
    test_claude(settings.claude_api_key)
    test_telegram(settings.telegram_bot_token, settings.telegram_chat_id)
    test_alpha_vantage(settings.alpha_vantage_api_key)

    print(f"\n{'─' * 50}")
    print("  Fine verifica.")
    print(f"{'─' * 50}\n")


if __name__ == "__main__":
    main()
