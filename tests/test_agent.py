"""
Tests for the FitFindr planning loop (agent.run_agent).

Run from the project root:  pytest

The deterministic search_listings runs for real; the two LLM-backed tools are
monkeypatched so the loop's control flow can be tested without network calls.
"""

import agent
from agent import _parse_query, run_agent
from utils.data_loader import get_example_wardrobe


# ── query parsing ─────────────────────────────────────────────────────────────

def test_parse_query_extracts_size_and_price():
    parsed = _parse_query("vintage graphic tee under $30, size M")

    assert parsed["size"] == "M"
    assert parsed["max_price"] == 30.0
    # The price and size phrases are stripped out of the description.
    assert "vintage graphic tee" in parsed["description"]
    assert "$30" not in parsed["description"]
    assert "size" not in parsed["description"].lower()


def test_parse_query_handles_missing_size_and_price():
    parsed = _parse_query("looking for a vintage graphic tee")

    assert parsed["size"] is None
    assert parsed["max_price"] is None
    assert "vintage graphic tee" in parsed["description"]


def test_parse_query_keyword_price_forms():
    assert _parse_query("jeans below 25")["max_price"] == 25.0
    assert _parse_query("jacket less than 40")["max_price"] == 40.0
    assert _parse_query("boots max $50")["max_price"] == 50.0


# ── planning loop ─────────────────────────────────────────────────────────────

def test_run_agent_happy_path(monkeypatch):
    """A matching query flows through all three tools and populates the session."""
    monkeypatch.setattr(agent, "suggest_outfit", lambda item, wardrobe: "Wear it with jeans.")
    monkeypatch.setattr(agent, "create_fit_card", lambda outfit, item: "Thrifted gold.")

    session = run_agent("vintage denim jeans under $50", get_example_wardrobe())

    assert session["error"] is None
    assert session["selected_item"] is not None
    assert len(session["search_results"]) > 0
    # selected_item is the top-ranked search result.
    assert session["selected_item"] is session["search_results"][0]
    assert session["outfit_suggestion"] == "Wear it with jeans."
    assert session["fit_card"] == "Thrifted gold."


def test_run_agent_no_results_returns_early(monkeypatch):
    """An impossible query sets error and skips the downstream tools (failure mode)."""
    def must_not_run(*args, **kwargs):
        raise AssertionError("downstream tools must not run when search is empty")

    monkeypatch.setattr(agent, "suggest_outfit", must_not_run)
    monkeypatch.setattr(agent, "create_fit_card", must_not_run)

    session = run_agent("designer ballgown size XXS under $5", get_example_wardrobe())

    assert session["error"] is not None
    assert session["search_results"] == []
    assert session["selected_item"] is None
    assert session["outfit_suggestion"] is None
    assert session["fit_card"] is None
