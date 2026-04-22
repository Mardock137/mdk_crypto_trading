from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from src.agents.performance_reviewer import (
    PerformanceReviewerAgent,
    _parse_performance_review,
)
from src.core.contracts import (
    InvestmentMandate,
    MandateAdherence,
    PerformanceReviewerInput,
    PerformanceStats,
)


def _make_mandate() -> InvestmentMandate:
    return InvestmentMandate(
        max_drawdown_pct=15.0,
        horizon="Intraday to swing",
        max_position_pct=100.0,
    )


def _make_stats() -> PerformanceStats:
    return PerformanceStats(
        period_start="2026-04-14",
        period_end="2026-04-20",
        total_cycles=28,
        buy_executed=1,
        sell_executed=0,
        hold_count=24,
        sell_failed=2,
        hold_ratio=0.857,
        strong_bullish_ignored=3,
        strong_bearish_ignored=0,
        realized_pnl_usdc=0.0,
        avg_pnl_pct=0.0,
        days_without_executed_trade=6,
    )


def _make_input() -> PerformanceReviewerInput:
    return PerformanceReviewerInput(
        symbol="BTCUSDC",
        mandate=_make_mandate(),
        stats=_make_stats(),
        days_analyzed=7,
    )


# ---------- Parsing ----------


def test_parse_aligned() -> None:
    data = {
        "summary": "Tutto ok.",
        "mandate_adherence": "ALIGNED",
        "suggestions": ["Mantenere disciplina"],
    }
    result = _parse_performance_review(data)

    assert result.summary == "Tutto ok."
    assert result.mandate_adherence is MandateAdherence.ALIGNED
    assert result.suggestions == ["Mantenere disciplina"]


def test_parse_drifting() -> None:
    data = {
        "summary": "Troppi HOLD.",
        "mandate_adherence": "DRIFTING",
        "suggestions": ["Agire sui segnali forti", "Ridurre esitazione"],
    }
    result = _parse_performance_review(data)

    assert result.mandate_adherence is MandateAdherence.DRIFTING
    assert len(result.suggestions) == 2


def test_parse_misaligned() -> None:
    data = {
        "summary": "Zero trade in settimana.",
        "mandate_adherence": "MISALIGNED",
        "suggestions": ["Rivedere soglie di ingresso"],
    }
    result = _parse_performance_review(data)

    assert result.mandate_adherence is MandateAdherence.MISALIGNED


def test_parse_missing_fields_raises() -> None:
    with pytest.raises(ValueError, match="Campi mancanti"):
        _parse_performance_review({"summary": "x"})


def test_parse_empty_dict_raises() -> None:
    with pytest.raises(ValueError, match="dict vuoto"):
        _parse_performance_review({})


def test_parse_accepts_string_suggestions() -> None:
    """_ensure_list_of_str deve gestire il caso in cui suggestions e una stringa."""
    data = {
        "summary": "x",
        "mandate_adherence": "ALIGNED",
        "suggestions": "Solo un suggerimento",
    }
    result = _parse_performance_review(data)

    assert result.suggestions == ["Solo un suggerimento"]


# ---------- Agent run ----------


def test_agent_run_calls_llm_and_parses_response() -> None:
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "summary": "Sistema in drifting.",
        "mandate_adherence": "DRIFTING",
        "suggestions": ["Agire sui segnali forti"],
    }

    agent = PerformanceReviewerAgent(llm=mock_llm)
    mock_prompt = MagicMock()
    mock_prompt.read_text.return_value = "system prompt"
    with patch("src.agents.base_agent.time.sleep"):
        with patch.object(
            type(agent), "prompt_path",
            new_callable=PropertyMock, return_value=mock_prompt,
        ):
            result = agent.run(_make_input())

    assert result.mandate_adherence is MandateAdherence.DRIFTING
    mock_llm.generate_json.assert_called_once()
    _, payload = mock_llm.generate_json.call_args.args
    assert payload["symbol"] == "BTCUSDC"
    assert payload["days_analyzed"] == 7
    assert "stats" in payload and "mandate" in payload
