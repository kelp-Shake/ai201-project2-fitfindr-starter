# FitFindr 🛍️

FitFindr is a multi-tool AI agent that helps users find secondhand clothing listings and style them. A planning loop orchestrates three tools and passes state between them through a single session dictionary, so the user describes the item only once.

I built FitFindr to make thrifting less of a hassle. You describe what you want and it finds a listing, styles it with what's already in your wardrobe, and writes a caption you could actually post. The whole idea was to chain three tools through one planning loop so you only describe the item once and the agent carries it the rest of the way.

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (free key at [console.groq.com](https://console.groq.com)):

```
GROQ_API_KEY=your_key_here
```

Run the app:

```bash
python app.py
```

Then open the URL printed in your terminal (usually `http://localhost:7860`).

Run the tests:

```bash
pytest tests/
```

---

## Tool Inventory

> These inputs and return values match the actual function signatures in `tools.py`.

### 1. `search_listings`
- **Signature:** `search_listings(description: str, size: str | None = None, max_price: float | None = None) -> list[dict]`
- **Inputs:**
  - `description` (str): keywords describing the item (e.g. `"vintage graphic tee"`)
  - `size` (str | None): size to filter by, case-insensitive substring match (`"M"` matches `"S/M"`); `None` skips size filtering
  - `max_price` (float | None): inclusive price ceiling; `None` skips price filtering
- **Output:** `list[dict]`: matching listing dicts sorted by relevance (best match first); `[]` when nothing matches
- **Purpose:** Search the mock listings dataset. Applies the price and size hard filters, then scores survivors by keyword overlap (count of query words appearing across title, description, style_tags, and colors) and drops listings with no overlap. Deterministic, no LLM.

### 2. `suggest_outfit`
- **Signature:** `suggest_outfit(new_item: dict, wardrobe: dict) -> str`
- **Inputs:**
  - `new_item` (dict): the listing dict the user is considering
  - `wardrobe` (dict): a wardrobe dict with an `"items"` key (a list of wardrobe-item dicts); may be empty
- **Output:** `str`: outfit/styling suggestions (never empty)
- **Purpose:** Ask the LLM for styling ideas. If the wardrobe has items, it formats them into the prompt and suggests outfits that name owned pieces; if the wardrobe is empty, it returns general styling advice for the item.

### 3. `create_fit_card`
- **Signature:** `create_fit_card(outfit: str, new_item: dict) -> str`
- **Inputs:**
  - `outfit` (str): the outfit suggestion from `suggest_outfit`
  - `new_item` (dict): the listing dict for the item
- **Output:** `str`: a casual OOTD-style social-media caption, or a descriptive error string if `outfit` is empty
- **Purpose:** Generate a short, shareable caption that mentions the item name, price, and platform once each, captures the outfit vibe, and varies across runs (higher LLM temperature).

---

## How the Planning Loop Works

The loop lives in `run_agent(query: str, wardrobe: dict) -> dict` in `agent.py`. It is **conditional**, not a fixed sequence. What `search_listings` returns decides whether the other two tools run at all.

1. **Parse**: `_parse_query` uses regex to extract `{description, size, max_price}` from the natural-language query (e.g. "under \$30" / "\$1,000" → `max_price`; "size M" → `size`). Regex was chosen over an LLM because parsing is cheap, deterministic, and easy to test.
2. **Search**: calls `search_listings(description, size, max_price)`.
3. **Branch on the result:**
   - **If the result list is empty** → set `session["error"]` to a helpful message and **return early**, *without* calling `suggest_outfit` or `create_fit_card`. This is the conditional behavior that proves the loop reacts to its inputs rather than always running all three tools.
   - **Otherwise** → store the results, select `results[0]` as `selected_item`, then call `suggest_outfit(selected_item, wardrobe)` followed by `create_fit_card(outfit, selected_item)`.
4. **Return** the completed session.

The thing I wanted to get right here is that the loop reacts to what search returns instead of just running all three tools every time. If search comes back empty there is nothing to style or caption, so it stops and reports why rather than calling the other two tools with empty input.

---

## State Management

The session dict created by `_new_session` is the **single source of truth** for one interaction. Each tool reads its input from the session and writes its output back, so data flows through the session rather than being re-entered by the user. For example, the item found by `search_listings` is stored once and read by both `suggest_outfit` and `create_fit_card`.

| Field | Written when | Holds |
|-------|-------------|-------|
| `query` | session created | the original user query |
| `parsed` | after parsing | `{description, size, max_price}` |
| `search_results` | after search | list of matching listing dicts |
| `selected_item` | after a non-empty search | the top result (`results[0]`) |
| `wardrobe` | session created | the user's wardrobe dict |
| `outfit_suggestion` | after `suggest_outfit` | the styling string |
| `fit_card` | after `create_fit_card` | the caption string |
| `error` | on early termination | a helpful message (else `None`) |

---

## Error Handling

| Tool | Failure mode | Strategy |
|------|-------------|----------|
| `search_listings` | No listings match the query | Returns `[]` (never raises). The loop sets `session["error"]` to a helpful, actionable message and returns early. |
| `suggest_outfit` | Wardrobe is empty | Returns general styling advice for the item instead of an empty string or crash. |
| `create_fit_card` | `outfit` is empty / whitespace | Returns a descriptive error string before any LLM call (no exception). |

**Concrete examples from testing (Milestone 5):**

- **`search_listings` no match:**
  ```
  >>> search_listings('designer ballgown', size='XXS', max_price=5)
  []
  >>> run_agent('designer ballgown size XXS under $5', get_example_wardrobe())['error']
  'No listings matched your search for "designer ballgown size XXS under $5". Try describing the item differently or loosening the size/price limit.'
  ```
  Returns an empty list, the loop skips the downstream tools, and the user gets a message that says what failed *and* what to try.

- **`suggest_outfit` empty wardrobe:** with `get_empty_wardrobe()` it returns general advice (e.g. pair with high-waisted jeans, layer under a cardigan) with no named wardrobe pieces.

- **`create_fit_card` empty outfit:**
  ```
  >>> create_fit_card('', item)
  'Could not create a fit card: no outfit suggestion was provided. Run suggest_outfit first to get an outfit to caption.'
  ```

---

## Spec Reflection

**One way the spec helped:** Writing the spec first made the build a lot easier. Because I wrote out each tool's inputs, return value, scoring rules, and failure mode in planning.md before I coded anything, I could build one tool at a time and check the generated function against my own spec before I ever ran it. It also made testing simpler, since I already knew the exact failure mode each tool had to handle (empty search, empty wardrobe, empty outfit) and could write a test for it instead of guessing what might go wrong.

**One way it diverged, and why:** The spec scored search on title, description, style_tags, and colors and dropped any listing with a score of 0. That worked fine until I tested a filters-only query like "size M under \$30". There are no keywords in that query, so every listing scored 0 and it came back empty, which felt broken to me. I changed `search_listings` so a query with no keywords keeps everything that passes the price and size filters instead of dropping it all. I also found the parser read a price like "\$1,000" as \$1 because the regex stopped at the comma, so now I strip the commas before parsing. Neither change was in the original spec; they both came out of testing the edges.

---

## AI Usage

**Instance 1, building the tools:** I used Claude to write the tools, but made it go one at a time. I gave it the Tool 1 spec from planning.md (the inputs, the keyword scoring rule, and the "return [] on no match" failure mode) and had it write `search_listings`, then I reviewed it against my signatures before running anything. At one point it added a fallback to `suggest_outfit` that returned canned advice if the LLM came back empty, and I had it taken out. That failure mode wasn't in my plan and the empty-wardrobe case was already handled, so keeping it would have made the code stop matching my spec.

**Instance 2, the planning loop:** For the loop I gave Claude my Planning Loop, State Management, and Architecture sections and had it write `run_agent` and the regex parser. The part I checked closely was the conditional path, that an empty search sets `session["error"]` and returns early without calling `suggest_outfit` or `create_fit_card`. I verified it with a test that fails if the downstream tools run on an empty search, so I knew the loop actually branches on what search returns instead of running all three tools every time.

---

## Project Structure

```
ai201-project2-fitfindr-starter/
├── agent.py          # planning loop (run_agent) + query parser
├── tools.py          # search_listings, suggest_outfit, create_fit_card
├── app.py            # Gradio UI (handle_query)
├── planning.md       # the spec, written before implementation
├── tests/            # pytest suite (one+ test per failure mode)
├── utils/            # data loaders
└── data/             # mock listings + wardrobe schema
```
