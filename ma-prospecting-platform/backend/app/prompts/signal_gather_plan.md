# Signal Gather & Display Plan

## Problem with the current design

- Signal extraction runs for ALL prospects (potentially 25+)
- For each prospect: discover transcripts → scrape quarter by quarter → Claude call per chunk → optional web press call
- That is 5-15 Claude calls per prospect, multiplied across 25 prospects = enormous latency and cost
- Source coverage is narrow: earnings transcripts + ad hoc web press, nothing else
- Private companies get synthetic signals (just product_mix_notes), which is useless

## What we want instead

- Show **8 prospects** with rich, sourced signals
- For each prospect: **one Claude call** with `web_search` that covers all 7 source types simultaneously
- Frontend shows signals grouped by source type, with clickable source URLs

---

## Architecture of the new "gather + extract" model

```
For each of the top-8 prospects:
    ONE Claude call
        tools: [web_search, max_uses=12]
        instruction: search across all 7 source types for THIS company
                     extract all M&A signals you find, cite source for each
        returns: JSON array of signals with source_type + source_url
```

All 7 source types in one call:
1. Company investor relations page (website disclosures)
2. Earnings call transcripts (BSE/NSE filings, Screener, company site)
3. Investor presentations (slide decks from IR page or exchanges)
4. SEBI disclosures (acquisitions, related-party transactions, substantial acquisitions)
5. Annual report — M&A strategy and capex guidance sections
6. Board resolutions — references to acquisition committees or inorganic mandates
7. Press and news — M&A announcements, deal signing, LOI mentions

Claude reads what it finds and extracts signals in the same call — no separate gather step.

---

## Changes Required

### 1. `config.py`

Add two new settings:
```python
signal_extraction_limit: int = 8      # only run signal extraction for top-N prospects
default_num_results: int = 8          # reduce display count from 25 to 8
```

`signal_extraction_limit` = how many prospects get the signal gather call.
These should be the same number (8) since we display exactly the prospects we have signals for.

---

### 2. `pipeline_orchestrator.py` — insert pre-sort before signal extraction

Current flow:
```
Step 3: generate prospects (N = user-specified, up to 25)
Step 4: extract signals (ALL N prospects)
Step 5: score all N, trim to num_results
```

New flow:
```
Step 3: generate prospects (still generate 20-30 candidates for quality)
        sort by profile-heuristic score (sector_relevance + persona priority)
        slice to signal_extraction_limit (8) — ONLY these get signal extraction
Step 4: extract signals — 1 call per prospect × 8 prospects
Step 5: score the 8 (with real signals), display all 8
```

**Pre-sort heuristic** (no extra Claude call — pure Python):
```python
RELEVANCE_SCORE = {"exact_match": 10, "adjacent": 7, "tangential": 4}
PERSONA_SCORE   = {"strategic": 3, "conglomerate": 2, "private_equity": 1}

def heuristic_score(p: Prospect) -> float:
    return RELEVANCE_SCORE.get(p.sector_relevance, 0) + PERSONA_SCORE.get(p.persona, 0)

prospects.sort(key=heuristic_score, reverse=True)
top_for_signals = prospects[:settings.signal_extraction_limit]
```

The remaining prospects (outside top 8) are dropped — they won't appear in the final output.

---

### 3. `models/signal.py` — add `source_type` field

Add a `SourceType` enum to distinguish document categories in the UI:

```python
class SourceType(str, Enum):
    EARNINGS_TRANSCRIPT     = "earnings_transcript"
    ANNUAL_REPORT           = "annual_report"
    SEBI_FILING             = "sebi_filing"
    INVESTOR_PRESENTATION   = "investor_presentation"
    BOARD_RESOLUTION        = "board_resolution"
    COMPANY_WEBSITE         = "company_website"
    PRESS                   = "press"
    UNKNOWN                 = "unknown"
```

Add `source_type: SourceType = SourceType.UNKNOWN` to `Signal` model.

---

### 4. `prompts/signal_extraction.py` — new function `build_signal_gather_prompt`

A single, self-contained prompt that instructs Claude to:
- Search for the company across all 7 source types (web_search tool)
- Read what it finds
- Extract signals as a JSON array

Key design: Claude is told to search *in sequence* (investor page first → transcripts → SEBI → annual report → board actions), not all at once. This gives the search budget structure.

```python
def build_signal_gather_prompt(
    company_name: str,
    ticker: str | None,
    target_profile: dict,
) -> str:
    """
    Single prompt for one Claude call (with web_search) that covers all 7 source types.
    Claude searches, reads, and extracts in one pass.
    """
```

The prompt body (see Section 5 below).

---

### 5. New prompt content for `build_signal_gather_prompt`

```
You are an M&A intelligence analyst. You will use the web_search tool to research
{company_name} ({ticker or 'unlisted'}) across 7 specific document sources and extract
acquisition signals relevant to the target company described below.

TARGET CONTEXT:
  Company: {target_profile.company_name}
  What they do: {description}
  Sector: {sector_l2} → {sector_l3}
  Key technologies: {key_technologies}
  Geography: {geographic_footprint}

SEARCH SEQUENCE — use web_search in this order, spending 1-2 searches per step:

STEP 1 — INVESTOR RELATIONS PAGE
  Search: "{company_name} investor relations disclosures site:nseindia.com OR bseindia.com"
  Also:   "{company_name} investor relations annual report"
  Look for: M&A strategy statements, acquisition intent, capital allocation commentary

STEP 2 — EARNINGS TRANSCRIPTS (last 2 years)
  Search: "{company_name} {ticker} earnings call transcript concall 2024 2025"
  Also try: "{company_name} Q3 Q4 FY25 conference call transcript"
  Sources to check: Screener.in, company IR page, NSE announcements
  Look for: acquisition intent statements, inorganic growth mentions, M&A pipeline references

STEP 3 — SEBI DISCLOSURES
  Search: "{company_name} {ticker} SEBI disclosure acquisition substantial acquisition"
  Also:   "{ticker} BSE NSE board resolution acquisition committee"
  Look for: SAST (Substantial Acquisition of Shares) filings, acquisition announcements,
            board resolutions forming M&A committees

STEP 4 — ANNUAL REPORT HIGHLIGHTS
  Search: "{company_name} annual report 2024 2025 M&A strategy capex inorganic"
  Look specifically for:
  - Capex guidance sections mentioning acquisition budget
  - Chairman/MD letter mentioning inorganic growth
  - Strategic priorities section mentioning acquisitions

STEP 5 — INVESTOR PRESENTATIONS
  Search: "{company_name} investor presentation 2024 2025 site:nseindia.com OR bseindia.com"
  Also:   "{company_name} analyst day presentation acquisition strategy"
  Look for: strategy slides mentioning M&A, bolt-on acquisition plans, sector expansion roadmaps

STEP 6 — BOARD RESOLUTIONS
  Search: "{company_name} board resolution acquisition committee inorganic 2024 2025"
  Look for: board approvals of M&A frameworks, acquisition mandate approvals, committee formations

AFTER SEARCHING:
Extract every signal you found that indicates {company_name} is interested in making acquisitions,
particularly in the target's sector ({sector_l2}), geography ({geography}), or technology area.

Signal types:
  acquisition_intent     → explicit M&A/acquisition language
  sector_expansion       → stated plans to grow in the target's L2/L3 sector
  technology_gap         → acknowledged need for the target's technology
  geographic_interest    → interest in the target's geography
  capex_signal           → acquisition war chest or unallocated capex budget
  board_action           → board-level M&A approvals or committee formation

Strength:
  high:   Named sector/technology/geography + active action verb (evaluating, in discussions, approved)
  medium: Clear directional intent, sector named, no confirmed action yet
  low:    Aspirational or circumstantial, space mentioned without intent

Return as JSON array:
[
  {
    "quote": "verbatim quote, copied exactly",
    "signal_type": "one of the 6 types above",
    "strength": "high | medium | low",
    "source_type": "earnings_transcript | annual_report | sebi_filing | investor_presentation | board_resolution | company_website | press",
    "source_document": "specific document name e.g. Q3 FY25 Earnings Call or FY24 Annual Report",
    "source_quarter": "e.g. Q3 FY25 or FY24 or N/A",
    "source_url": "the URL you read this from",
    "reasoning": "1-2 sentences: what the signal reveals + why it's relevant to acquiring the target"
  }
]

Return [] if no signals found after all searches.
CRITICAL: Only extract from documents you actually read via web_search — never from training data.
```

---

### 6. `clients/claude_search_client.py` — new function `gather_and_extract_signals`

Replace the entire `fetch_earnings_transcripts` + `fetch_ma_press_signals` → `_extract_from_transcript` chain for signal purposes with one function:

```python
async def gather_and_extract_signals(
    company_name: str,
    ticker: str | None,
    target_dict: dict,
) -> list[dict]:
    """
    One Claude call with web_search covering all 7 source types.
    Returns raw signal dicts (to be hydrated into Signal models by the caller).
    """
    prompt = build_signal_gather_prompt(company_name, ticker, target_dict)
    result = await call_claude(
        prompt=prompt,
        system_prompt=SIGNAL_SYSTEM_PROMPT,
        max_tokens=4096,
        temperature=0.0,
        response_json=True,
        label=f"signal_gather/{company_name[:30]}",
        tools=[_web_search_tool(max_uses=12)],   # 12 = ~2 per source type
        tool_choice=_force_web_search_choice(),
    )
    return result if isinstance(result, list) else []
```

---

### 7. `services/signal_extractor.py` — simplify `_extract_for_prospect`

The function currently has:
- Transcript cache lookup
- Quarter loop
- Prefilter check
- Per-chunk Claude calls
- Web press enrichment block

Replace with:

```python
async def _extract_for_prospect(prospect, target_dict, semaphore) -> list[Signal]:
    async with semaphore:
        cache_key = signal_key(prospect.ticker or prospect.company_name, "gather_v2", profile_hash(target_dict))
        cached = await cache_get(cache_key)
        if cached:
            logger.info("[SIGNALS] %-35s | cache HIT - %d signals", prospect.company_name, len(cached))
            return [Signal(**s) for s in cached]

        logger.info("[SIGNALS] %-35s | calling gather+extract (1 call)", prospect.company_name)
        raw = await gather_and_extract_signals(
            company_name=prospect.company_name,
            ticker=prospect.ticker,
            target_dict=target_dict,
        )
        signals = [
            Signal(
                id=str(uuid.uuid4()),
                prospect_id=prospect.id,
                quote=s.get("quote", ""),
                signal_type=SignalType(s.get("signal_type", "acquisition_intent")),
                strength=SignalStrength(s.get("strength", "low")),
                source_type=SourceType(s.get("source_type", "unknown")),
                source_document=s.get("source_document", ""),
                source_quarter=s.get("source_quarter", "N/A"),
                source_url=s.get("source_url"),
                reasoning=s.get("reasoning", ""),
            )
            for s in raw
            if s.get("quote") and s.get("signal_type") and s.get("strength")
        ]
        await cache_set(cache_key, [s.model_dump() for s in signals], ttl_seconds=86400 * 7)
        logger.info("[SIGNALS] %-35s | %d signals extracted", prospect.company_name, len(signals))
        return signals
```

Note: `_generate_private_signals` is kept for private companies that web_search cannot find enough on.
But with web_search enabled, private company signal gathering should work the same way — Claude just searches for whatever public information exists.

---

### 8. Frontend: `lib/types.ts`

Add `source_type` to the `Signal` interface:
```typescript
type SourceType =
  | "earnings_transcript"
  | "annual_report"
  | "sebi_filing"
  | "investor_presentation"
  | "board_resolution"
  | "company_website"
  | "press"
  | "unknown";

interface Signal {
  ...existing fields...
  source_type: SourceType;   // new
}
```

---

### 9. Frontend: `lib/constants.ts`

Add source type display config:
```typescript
export const SOURCE_TYPE_LABELS: Record<string, string> = {
  earnings_transcript:   "Earnings Call",
  annual_report:         "Annual Report",
  sebi_filing:           "SEBI Filing",
  investor_presentation: "Investor Presentation",
  board_resolution:      "Board Resolution",
  company_website:       "IR / Website",
  press:                 "Press",
  unknown:               "Source",
};

export const SOURCE_TYPE_COLORS: Record<string, string> = {
  earnings_transcript:   "bg-blue-50 text-blue-700 border-blue-200",
  annual_report:         "bg-purple-50 text-purple-700 border-purple-200",
  sebi_filing:           "bg-orange-50 text-orange-700 border-orange-200",
  investor_presentation: "bg-indigo-50 text-indigo-700 border-indigo-200",
  board_resolution:      "bg-red-50 text-red-700 border-red-200",
  company_website:       "bg-teal-50 text-teal-700 border-teal-200",
  press:                 "bg-gray-50 text-gray-700 border-gray-200",
  unknown:               "bg-gray-50 text-gray-500 border-gray-200",
};
```

---

### 10. Frontend: `components/results/SignalCard.tsx`

Replace the current single-line header with a two-row header:

Row 1: Source type badge (colored) + source quarter/period
Row 2: Signal type + strength badge

Body: verbatim quote in blockquote

Footer: reasoning + clickable "View source →" link if `source_url` present

```tsx
<div className={`border rounded-lg p-3 text-sm ${SIGNAL_STRENGTH_COLORS[signal.strength]}`}>
  <div className="flex items-center gap-2 mb-1">
    {/* Source type badge */}
    <span className={`text-xs font-medium px-2 py-0.5 rounded border ${SOURCE_TYPE_COLORS[signal.source_type]}`}>
      {SOURCE_TYPE_LABELS[signal.source_type]}
    </span>
    {/* Period */}
    <span className="text-xs opacity-60">{signal.source_quarter}</span>
    {/* Strength */}
    <span className="ml-auto text-xs font-medium capitalize">{signal.strength}</span>
  </div>

  <div className="text-xs opacity-60 mb-2">{signal.source_document}</div>

  <blockquote className="italic leading-relaxed mb-2">"{signal.quote}"</blockquote>

  <p className="text-xs opacity-70 not-italic mb-2">{signal.reasoning}</p>

  {signal.source_url && (
    <a href={signal.source_url} target="_blank" rel="noopener noreferrer"
       className="text-xs underline opacity-60 hover:opacity-100">
      View source →
    </a>
  )}
</div>
```

---

### 11. Frontend: `components/results/ExpandedProspect.tsx`

Group signals by source type instead of showing a flat list:

```tsx
// Group signals by source_type
const grouped = signal.reduce((acc, s) => {
  const key = s.source_type || "unknown";
  (acc[key] = acc[key] || []).push(s);
  return acc;
}, {} as Record<string, Signal[]>);

// Render each group with a header
{Object.entries(grouped).map(([type, sigs]) => (
  <div key={type}>
    <h5 className="text-xs font-semibold text-gray-400 uppercase mb-1 mt-3">
      {SOURCE_TYPE_LABELS[type]} ({sigs.length})
    </h5>
    {sigs.map(s => <SignalCard key={s.id} signal={s} />)}
  </div>
))}
```

Also add a signal source summary line at the top of the signals panel:
```tsx
<div className="text-xs text-gray-400 mb-3">
  {sp.signals.length} signal{sp.signals.length !== 1 ? 's' : ''} found
  across {Object.keys(grouped).length} source type{...}
</div>
```

---

## Implementation Order

| Step | File | What changes |
|------|------|-------------|
| 1 | `config.py` | Add `signal_extraction_limit = 8`, change `default_num_results = 8` |
| 2 | `models/signal.py` | Add `SourceType` enum + `source_type` field to `Signal` |
| 3 | `prompts/signal_extraction.py` | Add `build_signal_gather_prompt()` function |
| 4 | `clients/claude_search_client.py` | Add `gather_and_extract_signals()` function |
| 5 | `services/signal_extractor.py` | Rewrite `_extract_for_prospect` to use single gather call; add pre-sort logic |
| 6 | `services/pipeline_orchestrator.py` | Insert heuristic pre-sort + slice to `signal_extraction_limit` before step 4 |
| 7 | `lib/types.ts` | Add `source_type` to `Signal` interface |
| 8 | `lib/constants.ts` | Add `SOURCE_TYPE_LABELS`, `SOURCE_TYPE_COLORS` |
| 9 | `components/results/SignalCard.tsx` | Add source type badge + clickable source URL |
| 10 | `components/results/ExpandedProspect.tsx` | Group signals by source type, add summary line |

## What this achieves

| Metric | Before | After |
|--------|--------|-------|
| Prospects with signals | All (25+) | Top 8 only |
| Claude calls per prospect | 5-15 (per quarter + web press) | 1 |
| Source types covered | Earnings transcripts + ad hoc press | 7 structured types |
| Private company signals | Synthetic (product_mix_notes) | Real web search |
| Signal attribution | Document name + quarter | Source type badge + clickable URL |
| Signal grouping in UI | Flat list | Grouped by source type |
| Cache | Per-quarter | Per-prospect (7 days TTL) |
