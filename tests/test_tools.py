"""
Tests for the three FitFindr tools.

Run from the project root:  pytest

Each tool is tested in isolation, with at least one test per documented
failure mode (see planning.md → Error Handling).
"""

import tools
from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import (
    get_empty_wardrobe,
    get_example_wardrobe,
    load_listings,
)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def test_search_returns_results():
    """A plausible query returns a non-empty list of listing dicts."""
    results = search_listings("vintage denim jeans", size=None, max_price=None)

    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(item, dict) for item in results)
    # Every returned listing carries the documented fields.
    assert all("title" in item and "price" in item for item in results)


def test_search_sorted_by_relevance_descending():
    """Results come back ordered best-match-first (non-increasing score)."""
    results = search_listings("vintage denim jeans streetwear", None, None)

    def score(item):
        query = {"vintage", "denim", "jeans", "streetwear"}
        text = " ".join(
            [item["title"], item["description"]]
            + item["style_tags"]
            + item["colors"]
        ).lower()
        words = set(text.replace("/", " ").replace("—", " ").split())
        return len(query & words)

    scores = [score(item) for item in results]
    assert scores == sorted(scores, reverse=True)


def test_search_no_match_returns_empty_list():
    """An impossible query returns [] rather than raising (failure mode)."""
    results = search_listings("designer ballgown tuxedo", size="XXS", max_price=5.0)

    assert results == []


def test_search_price_filter_respected():
    """No returned listing exceeds the max_price ceiling."""
    cap = 30.0
    results = search_listings("vintage tee shirt", size=None, max_price=cap)

    assert len(results) > 0  # sanity: the query should match something under $30
    assert all(item["price"] <= cap for item in results)


def test_search_size_filter_case_insensitive_substring():
    """size='m' matches listings whose size contains M/m (e.g. 'S/M')."""
    results = search_listings("tee shirt top", size="m", max_price=None)

    assert all("m" in item["size"].lower() for item in results)


def test_search_empty_description_returns_filter_matches():
    """A size/price-only query (no keywords) returns everything passing the filters."""
    results = search_listings("", size="M", max_price=30.0)

    assert len(results) > 0  # filters-only browsing should not come back empty
    assert all("m" in item["size"].lower() for item in results)
    assert all(item["price"] <= 30.0 for item in results)


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def test_suggest_outfit_with_wardrobe(monkeypatch):
    """With a populated wardrobe, the prompt names owned pieces and the item."""
    captured = {}

    def fake_chat(prompt, temperature=0.7):
        captured["prompt"] = prompt
        return "Pair it with the baggy jeans and chunky sneakers."

    monkeypatch.setattr(tools, "_chat", fake_chat)

    item = load_listings()[0]
    wardrobe = get_example_wardrobe()
    result = suggest_outfit(item, wardrobe)

    assert isinstance(result, str) and result.strip()
    # The prompt should include the new item and at least one wardrobe piece by name.
    assert item["title"] in captured["prompt"]
    assert wardrobe["items"][0]["name"] in captured["prompt"]


def test_suggest_outfit_empty_wardrobe(monkeypatch):
    """With an empty wardrobe, it asks for general advice and never returns '' (failure mode)."""
    captured = {}

    def fake_chat(prompt, temperature=0.7):
        captured["prompt"] = prompt
        return "This piece pairs well with neutral basics."

    monkeypatch.setattr(tools, "_chat", fake_chat)

    item = load_listings()[0]
    result = suggest_outfit(item, get_empty_wardrobe())

    assert isinstance(result, str) and result.strip()
    assert "general styling advice" in captured["prompt"].lower()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def test_create_fit_card_empty_outfit_returns_error(monkeypatch):
    """An empty/whitespace outfit returns an error string without calling the LLM (failure mode)."""
    def boom(*args, **kwargs):
        raise AssertionError("LLM should not be called when outfit is empty")

    monkeypatch.setattr(tools, "_chat", boom)
    item = load_listings()[0]

    for bad in ("", "   ", "\n\t"):
        result = create_fit_card(bad, item)
        assert isinstance(result, str) and result.strip()
        assert "could not create a fit card" in result.lower()


def test_create_fit_card_includes_item_details(monkeypatch):
    """With a real outfit, the prompt carries the item name, price, and platform."""
    captured = {}

    def fake_chat(prompt, temperature=0.7):
        captured["prompt"] = prompt
        captured["temperature"] = temperature
        return "Thrifted these and never looking back."

    monkeypatch.setattr(tools, "_chat", fake_chat)
    item = load_listings()[0]

    result = create_fit_card("Paired with white sneakers and a tank top.", item)

    assert isinstance(result, str) and result.strip()
    assert item["title"] in captured["prompt"]
    assert str(item["price"]) in captured["prompt"]
    assert item["platform"] in captured["prompt"]
    # Caption generation uses a higher temperature for variety.
    assert captured["temperature"] >= 1.0
