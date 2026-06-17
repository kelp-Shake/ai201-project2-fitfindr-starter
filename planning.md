# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

Project Instructions Description:
searches the mock listings dataset and returns matching items. Must handle the case where no matches are found.


**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->

this tool will take an input break down the requirements search it against the mock listings and returns the most relevant results if found otherwise it will return nothing 

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): The item description; kind, type, style of item 
- `size` (str): Size of clothing item 
- `max_price` (float): the max price of a listing that is used in the search 

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
Returns a list of dictionaries for listings in order based of relevancy 

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
return a empty list 

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
The tool will search the new item against items the users wardrobe to find a matching existing items that will make a completed outfit. if there isn't any relevant or enough items to create outfit match no suggestion will be returned 

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): listing dictionary for associated item
- `wardrobe` (dict): items key with vals of list of items 

**What it returns:**
<!-- Describe the return value -->
returns a string of an outfit suggestion and style suggestion if an outfit is found 

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
return a string default message that there isn't a matching outfit for the new item 

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Creates a description for social media posts for the passed outfit and new item with a unique caption for different inputs 

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): outfit suggestion and style suggestion if an outfit
- `new_item` (dict): listing dictionary for associated item

**What it returns:**
<!-- Describe the return value -->
(str) caption that describes the fit created with the outfit and new item 

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
(str) identifies what part of outfit/new item/generated caption failed and stops 

**Complete Interaction**
Fit finder needs to validate inputs for the functions, use the inputted parms to search in the associated dict/list to create responses for the user created prompts. 
+ the finder will create outfits, add items to a wardrobe, and create captions for outfits in a wardrobe.
+ search for item: filter parms agaianst listings json -> return item type 
+ create outfit: filter given wardrobe and create an outfit including the given item type to create a full outfit (top/bottom/ clothing), shoes -> return outfit string 
+ create caption: filter item of target(new item), outfit for associated item genrate a caption based of all items notes and parms for a caption for a social media post 


---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

+ search listings
  + take user response break it down for search listing by using regex to filter out (size, description -> clothing type, max_price) against category, title, description then store in parsed dict
  + search listing is then ran with the passed parsed parms and words from user input against the listings json, then a keyword match is computed against each listing to sort based off most matched words, then return the listings in order of highest -> lowest keyword match
  + IF search_results is empty -> set session error to a relevant "no matches found" message and return the session early, WITHOUT calling suggest_outfit or create_fit_card
  + ELSE -> store the sorted list in session search_results, select the top result (results[0]) as the new item for the rest of the session, and store it in session selected_item
+ suggest outfit
  + given the user inputted wardrobe
    + if there is a wardrobe, format the items into a prompt then ask the llm for suggestions
      + create prompt (i want to create an outfit with the new item, I have a wardrobe with the passed wardrobe json, create a full outfit suggestion)
    + if the wardrobe is empty, return general style advice for the new item
  + style advice: generated by llm based off (what kinds of items pair well, what vibe it suits, etc)
  + return a string of the outfit suggested by llm, store result in session outfit_suggestion
+ fit card
  + using the session outfit_suggestion and the new item listing, create a caption
  + if there is no outfit, return an error message string
  + the social media style caption will
    + Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)
  + store the caption in session fit_card
+ return
  + the completed session


---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->
The agent creates a new session dict at the start of each interaction that acts as the single source of truth while the agent runs. Each tool reads its input from the session and writes its result back into it, so data flows through the session rather than being re-entered by the user. The fields tracked are: parsed (the regex-extracted description/size/max_price), search_results (the list from search_listings), selected_item (results[0], passed into suggest_outfit), outfit_suggestion (the string from suggest_outfit, passed into create_fit_card), fit_card (the final caption), and error (set if the interaction ends early). For example, the item found by search_listings is stored in selected_item and read directly by both suggest_outfit and create_fit_card — the user never re-enters it.


---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | return empty list. agent sets the  session error to a helpful message |
| suggest_outfit | Wardrobe is empty | return  str general style advice based of the item from listings |
| create_fit_card | Outfit input is missing or incomplete | error string a descriptive error message |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

```
User query
    │
    ▼
Planning Loop (run_agent)
    │
    ├─► parse query (regex) → session["parsed"] = {description, size, max_price}
    │
    ├─► search_listings(description, size, max_price)
    │       │
    │       │ results == []
    │       ├──► session["error"] = "no matches found..." → RETURN session (skip remaining tools)
    │       │
    │       │ results != []
    │       ▼
    │   session["search_results"] = results
    │   session["selected_item"]  = results[0]
    │       │
    │       ▼
    ├─► suggest_outfit(selected_item, wardrobe)
    │       │
    │   session["outfit_suggestion"] = "..."
    │       │
    │       ▼
    └─► create_fit_card(outfit_suggestion, selected_item)
            │
        session["fit_card"] = "..."
            │
            ▼
        RETURN session
```

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

use claude to help with planning
**Milestone 3 — Individual tool implementations:**

**Tool used:** Claude (Claude Code). For each tool I gave it that tool's spec from this
planning.md — the input parameters, return value, scoring rules, and failure mode — and
asked it to implement one function at a time, reviewing each against the spec before running it.

+ **search_listings** — implemented with `load_listings()` from the data loader. No LLM is used;
  it's deterministic. A shared `tokenize()` helper lowercases text and splits it into
  alphanumeric word tokens. The function applies two hard filters (price ≤ `max_price`, and a
  case-insensitive substring size match so "M" matches "S/M"), then scores each survivor by
  keyword overlap = the count of distinct query words appearing across
  title + description + style_tags + colors (equal weight), drops score-0 listings, and returns
  the rest sorted by score descending (stable sort keeps dataset order on ties).
  If the query has no keywords at all (a size/price-only search like "size M under $30"),
  it keeps every listing that passed the hard filters instead of dropping them all as score-0,
  so filters-only browsing still returns results.
  *Decision — regex vs. LLM for parsing:* parsing the user query into
  {description, size, max_price} stays as regex in the planning loop (Milestone 4), not an LLM
  call — it's cheap, deterministic, and easy to test. The LLM is reserved for the two
  generative tools below. Known limitation: no synonym matching ("tee" won't match "shirt").

+ **suggest_outfit** — uses the Groq LLM (`llama-3.3-70b-versatile`) via a shared `_chat()` helper.
  Branches on whether `wardrobe["items"]` is empty: if populated, it formats the owned pieces into
  the prompt and asks for 1-2 outfits that name those pieces; if empty, it asks for general styling
  advice for the item (the documented failure mode). Returns the LLM string.

+ **create_fit_card** — uses the LLM at a higher temperature (1.0) so captions vary across runs.
  Guards against an empty/whitespace `outfit` by returning a descriptive error string before any
  LLM call (the documented failure mode). Otherwise prompts for a casual OOTD-style caption that
  mentions the item name, price, and platform once each.

**How I verified each tool before moving on:** pytest suite in `tests/test_tools.py`, at least one
test per documented failure mode. search_listings: returns results, sorted descending, `[]` on an
impossible query, price ceiling respected, size substring match. suggest_outfit and create_fit_card:
the LLM call is monkeypatched so the tests assert branch logic and prompt contents (item/price/
platform present, empty-wardrobe → general-advice prompt, empty-outfit → error string with no LLM
call) without hitting the network. Both LLM tools were also smoke-tested against the live API.

**Milestone 4 — Planning loop and state management:**

**Tool used:** Claude (Claude Code). I gave it the Planning Loop, State Management, and
Architecture sections above and asked it to implement `run_agent` and the query parser to match
that flow.

+ **Query parsing (`_parse_query`)** — regex, not an LLM (the decision from Milestone 3). It pulls
  `max_price` from forms like "under $30", "below 25", "less than 40", "max $50", "up to 20", or a
  bare "$30" (thousands separators like "$1,000" are handled — commas are stripped before
  parsing, so it reads as 1000.0); `size` from the token after "size" ("size M", "size XXS",
  "size 9"); and `description`
  is the query with those price/size phrases stripped. Because search_listings tokenizes the
  description, any leftover filler words simply don't match a listing and add nothing to the score.

+ **Planning loop (`run_agent`)** — follows the 7 steps from the diagram: build a fresh session
  with `_new_session`, parse the query into `session["parsed"]`, call `search_listings`. If the
  results are empty it sets `session["error"]` to a helpful message and returns early *without*
  calling the LLM tools. Otherwise it stores the results, selects `results[0]` as
  `session["selected_item"]`, calls `suggest_outfit(selected, wardrobe)` →
  `session["outfit_suggestion"]`, then `create_fit_card(outfit, selected)` →
  `session["fit_card"]`, and returns the session.

+ **State management** — the session dict is the single source of truth: each tool reads its input
  from the session and writes its output back, so the selected item flows from search into both
  generative tools without the user re-entering anything.

**How I verified it:** pytest in `tests/test_agent.py`. Parsing tests cover size+price extraction,
missing size/price, and the keyword price forms. Loop tests monkeypatch the two LLM tools (leaving
the deterministic search real) to cover the happy path (all session fields populated, selected_item
is the top result) and the no-results failure mode (error set; search_results empty; selected_item,
outfit_suggestion, and fit_card all None; downstream tools never called). Both paths were also run
live end-to-end via `python agent.py`.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->

parsed = {description: "vintage graphic tee", size: "M", max_price: 30.0}. Calls search_listings("vintage graphic tee", "M", 30.0), which returns 3 matching listing dicts sorted by keyword score. Stores them in search_results; sets selected_item = results[0] (the top match, e.g. the Faded Band Tee).

**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
Calls suggest_outfit(selected_item, wardrobe) with that band tee dict and the example wardrobe. Returns a styling string pairing it with owned pieces (baggy jeans, chunky sneakers). Stores it in outfit_suggestion.

**Step 3:**
<!-- Continue until the full interaction is complete -->

Calls create_fit_card(outfit_suggestion, selected_item). Returns a casual OOTD-style caption mentioning the item name, price, and platform. Stores it in fit_card.

**Final output to user:**
<!-- What does the user actually see at the end? -->
The user sees the top listing, the outfit idea, and the fit card in the three panels.
