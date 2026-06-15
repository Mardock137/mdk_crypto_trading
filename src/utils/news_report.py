from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.core.contracts import NewsDigest


def write_news_report(
    symbol: str,
    digest: NewsDigest,
    hours_analyzed: int,
    reports_dir: str | Path,
    now: datetime | None = None,
) -> Path:
    """Serializza un NewsDigest in markdown e lo salva in ``reports_dir/YYYY-MM-DD_HH-MM.md``.

    Il nome file usa il separatore ``_`` tra data e ora (Windows-safe, niente ``:``),
    ed è ordinabile cronologicamente. Ritorna il path del file scritto.
    """
    reference = now or datetime.now(timezone.utc)
    target_dir = Path(reports_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = reference.strftime("%Y-%m-%d_%H-%M") + ".md"
    file_path = target_dir / filename
    file_path.write_text(
        _format_news_markdown_report(symbol, digest, hours_analyzed, reference),
        encoding="utf-8",
    )
    return file_path


def _format_news_markdown_report(
    symbol: str,
    digest: NewsDigest,
    hours_analyzed: int,
    reference: datetime,
) -> str:
    timestamp_str = reference.strftime("%Y-%m-%d %H:%M UTC")

    key_events_block = "\n".join(f"- {e}" for e in digest.key_events) or "- (nessun evento chiave)"
    risk_flags_block = "\n".join(f"- {f}" for f in digest.risk_flags) or "- (nessun risk flag)"

    return (
        f"# News Review — {timestamp_str}\n"
        "\n"
        f"**Simbolo**: {symbol}\n"
        f"**Finestra analizzata**: ultime {hours_analyzed} ore\n"
        f"**Sentiment complessivo**: {digest.overall_sentiment.value}\n"
        "\n"
        "## Sintesi\n"
        "\n"
        f"{digest.summary}\n"
        "\n"
        "## Eventi chiave\n"
        "\n"
        f"{key_events_block}\n"
        "\n"
        "## Risk flag\n"
        "\n"
        f"{risk_flags_block}\n"
    )

