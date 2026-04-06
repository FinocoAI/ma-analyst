# M&A Prospecting Platform -- MVP Solution Design Document

**Version:** 1.0
**Date:** 2026-04-02
**Status:** Draft

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Solution Overview](#3-solution-overview)
4. [Tech Stack](#4-tech-stack)
5. [Repository & Folder Structure](#5-repository--folder-structure)
6. [Data Models](#6-data-models)
7. [Prompt Chain Architecture](#7-prompt-chain-architecture)
8. [API Endpoint Design](#8-api-endpoint-design)
9. [Frontend Component Hierarchy](#9-frontend-component-hierarchy)
10. [Phase Breakdown & Milestones](#10-phase-breakdown--milestones)
11. [Build Order & Dependency Graph](#11-build-order--dependency-graph)
12. [Cost Analysis](#12-cost-analysis)
13. [Risk Areas & Mitigations](#13-risk-areas--mitigations)
14. [Architectural Decisions & Trade-offs](#14-architectural-decisions--trade-offs)
15. [MVP Scope vs Future Versions](#15-mvp-scope-vs-future-versions)

---

## 1. Executive Summary

We are building an **AI-powered M&A Prospecting Platform** that automates buyer discovery for sell-side investment banking mandates. When a company is up for sale (e.g., a Swiss air pollution control firm), the platform identifies, profiles, and ranks potential Indian acquirers -- citing real acquisition signals from earnings transcripts, annual reports, and SEBI filings.

The product is NOT a heavy ML pipeline. It is a **prompt-orchestration layer**: the user sets variables (target company, buyer persona, revenue range), and the system constructs and chains Claude prompts to scrape, profile, match, and rank potential acquirers -- citing every signal back to its source.

---

## 2. Problem Statement

When an investment bank takes a sell-side mandate, the team needs to find who would want to buy the target company. Today this takes **weeks of manual work**:

- Reading earnings call transcripts
- Scanning annual reports
- Checking SEBI filings
- Hunting for sentences like *"we are exploring inorganic growth in environmental services"*

This is slow, expensive, inconsistent, and doesn't scale.

**Our USP:** Finding the right list of buyer companies that can acquire the target company, backed by real signals from public disclosures, with every recommendation cited to its source.

---

## 3. Solution Overview

### 5-Step Prompt Chain

```
User pastes target company URL (e.g., elex.ch)
    |
    v
Step 1: PROFILE -- Scrape website, Claude extracts structured profile
    |
    v
Step 2: PROSPECT -- Two parallel tracks find 25-50 Indian buyer candidates
    |          Track A: Listed companies (FMP + Exa + Claude)
    |          Track B: Private companies (Exa + Claude)
    |
    v
Step 3: SIGNALS -- Fetch earnings transcripts, Claude extracts acquisition signals
    |              with exact quotes and citations
    |
    v
Step 4: SCORE -- Claude scores each buyer across 6 weighted dimensions
    |
    v
Step 5: CHAT -- Conversational drill-down with full context
```

### User-Configurable Variables

| Variable | UI Element | How It Shapes the Prompt |
|----------|-----------|--------------------------|
| Target company URL | Text input | Scraped content injected into profiling prompt |
| Target sector | Auto-filled, editable | Determines which companies to search and transcripts to analyze |
| Buyer persona | Multi-select: Strategic, PE, Conglomerate | Filters prospect list, changes scoring priorities |
| Revenue range | Min-Max slider | Constraint injected: "Only include companies with revenue > target" |
| Geography | Dropdown (India for V1) | Constrains prospect search |
| Signal keywords | Optional text input | Appended to signal extraction prompt |
| Matching weights | 6 sliders (sector, tech, geo, financial, timing, product) | Injected into scoring prompt |
| Number of results | Dropdown: 10 / 25 / 50 | Controls pipeline throughput |

### Success Criteria (Demo)

1. User enters URL -> ranked list of 15-20 Indian companies in **< 10 minutes**
2. Top 5 ranked companies make intuitive sense to a sector expert
3. At least 3-5 companies show **real acquisition signals with exact transcript quotes**
4. Every signal is cited with source and quarter
5. Expandable rows show clear reasoning for each ranking

---

## 4. Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **LLM** | Anthropic SDK (direct) | Full control, Batch API support, no framework overhead |
| **Orchestration** | `async/await` + `asyncio.gather()` | Pipeline is linear with one fan-out; no framework needed |
| **Backend** | Python + FastAPI | Async-native, fast, great Pydantic integration |
| **Pipeline state** | Pydantic models | Type-safe structured data flowing between steps |
| **Database** | SQLite (aiosqlite) | Single-user MVP, zero-config, easy migration to Postgres later |
| **Caching** | SQLite (same DB) | Cache transcripts and signal extractions |
| **Web scraping** | httpx + BeautifulSoup | Lightweight, handles most company sites |
| **Company discovery** | Exa API | Semantic search, far more reliable than scraping Google |
| **Financial data** | FMP API | Earnings transcripts, company financials |
| **Frontend** | Next.js (React) + Tailwind CSS | SaaS-style dashboard UI |
| **Containerization** | Docker Compose | Local dev: backend + frontend |

### API Keys Required

| Service | Purpose | Priority |
|---------|---------|----------|
| **Anthropic API** | All Claude calls (profiling, prospecting, signals, scoring, chat) | Required |
| **FMP API** | Earnings call transcripts, company financials | Required |
| **Exa API** | Company discovery (listed + private) | Required |

---

## 5. Repository & Folder Structure

```
ma-prospecting-platform/
|
|-- backend/
|   |-- app/
|   |   |-- main.py                        # FastAPI app, CORS, lifespan
|   |   |-- config.py                      # Settings via pydantic-settings (env vars)
|   |   |-- dependencies.py               # Dependency injection (db, anthropic client)
|   |   |
|   |   |-- models/                        # Pydantic models (pipeline state, API schemas)
|   |   |   |-- __init__.py
|   |   |   |-- target.py                  # TargetProfile, TargetProfileRequest
|   |   |   |-- prospect.py               # Prospect, ProspectList, BuyerPersona enum
|   |   |   |-- signal.py                 # Signal, SignalType enum, SignalStrength enum
|   |   |   |-- scoring.py               # DimensionScore, ScoredProspect, ScoringWeights
|   |   |   |-- pipeline.py              # PipelineRun, PipelineStatus enum
|   |   |   |-- chat.py                  # ChatMessage, ChatRequest, ChatResponse
|   |   |   |-- common.py               # Citation, SourceReference
|   |   |
|   |   |-- prompts/                      # Prompt templates as plain Python string constants
|   |   |   |-- __init__.py
|   |   |   |-- target_profiling.py       # build_profile_prompt()
|   |   |   |-- prospect_generation.py    # build_prospect_prompt()
|   |   |   |-- signal_extraction.py      # build_signal_prompt()
|   |   |   |-- scoring.py               # build_scoring_prompt()
|   |   |   |-- chat.py                  # build_chat_system_prompt()
|   |   |
|   |   |-- services/                     # Business logic & orchestration
|   |   |   |-- __init__.py
|   |   |   |-- pipeline_orchestrator.py  # run_pipeline() -- coordinates all steps
|   |   |   |-- target_profiler.py        # scrape_and_profile()
|   |   |   |-- prospect_generator.py     # generate_prospects() -- two parallel tracks
|   |   |   |-- signal_extractor.py       # extract_signals() -- fan-out across transcripts
|   |   |   |-- scorer.py                # score_prospects()
|   |   |   |-- chat_service.py          # handle_chat_message()
|   |   |
|   |   |-- clients/                      # External API wrappers
|   |   |   |-- __init__.py
|   |   |   |-- anthropic_client.py       # call_claude(), retries, token counting
|   |   |   |-- fmp_client.py            # get_transcripts(), get_company_profile()
|   |   |   |-- exa_client.py            # search_companies(), find_similar()
|   |   |   |-- scraper.py              # scrape_url(), extract_text()
|   |   |
|   |   |-- cache/                        # Caching layer
|   |   |   |-- __init__.py
|   |   |   |-- cache_manager.py          # get/set/invalidate (SQLite-backed)
|   |   |   |-- keys.py                  # Cache key builders
|   |   |
|   |   |-- routers/                      # FastAPI route handlers
|   |   |   |-- __init__.py
|   |   |   |-- pipeline.py             # POST /run, GET /status, PUT /profile, POST /rescore
|   |   |   |-- prospects.py            # GET /prospects, GET /prospects/{id}
|   |   |   |-- chat.py                 # POST /chat, GET /chat/history
|   |   |   |-- health.py              # GET /health
|   |   |
|   |   |-- storage/                      # Persistence
|   |   |   |-- __init__.py
|   |   |   |-- database.py             # SQLite async setup
|   |   |   |-- repositories.py         # CRUD operations
|   |   |
|   |   |-- utils/
|   |       |-- __init__.py
|   |       |-- text_processing.py       # Chunking, token counting, text cleaning
|   |       |-- retry.py                # Exponential backoff for API calls
|   |
|   |-- tests/
|   |   |-- test_prompts/               # Prompt eval tests (gold-standard transcripts)
|   |   |-- test_services/
|   |   |-- test_routers/
|   |   |-- fixtures/                   # Sample transcripts, profiles, expected outputs
|   |
|   |-- pyproject.toml
|   |-- Dockerfile
|   |-- .env.example
|
|-- frontend/
|   |-- src/
|   |   |-- app/                         # Next.js App Router
|   |   |   |-- layout.tsx              # Root layout: sidebar + main area
|   |   |   |-- page.tsx               # Landing/redirect
|   |   |   |-- prospecting/
|   |   |       |-- page.tsx           # Main prospecting view
|   |   |
|   |   |-- components/
|   |   |   |-- layout/
|   |   |   |   |-- Sidebar.tsx         # Left nav: Prospecting (active), Buy-side (disabled)
|   |   |   |   |-- MainLayout.tsx      # Three-column layout shell
|   |   |   |
|   |   |   |-- target/
|   |   |   |   |-- TargetInputForm.tsx       # URL input + filters + "Analyse" button
|   |   |   |   |-- TargetProfileCard.tsx     # Editable profile display after Step 1
|   |   |   |   |-- WeightSliders.tsx         # Six dimension weight sliders
|   |   |   |
|   |   |   |-- results/
|   |   |   |   |-- ResultsSummaryBar.tsx     # Total Matches, Strong Signals, Avg Score, Sources
|   |   |   |   |-- ResultsTable.tsx          # Main ranked table
|   |   |   |   |-- ProspectRow.tsx           # Single expandable row
|   |   |   |   |-- ExpandedProspect.tsx      # Signals, dimension scores, reasoning
|   |   |   |   |-- SignalCard.tsx            # Individual signal with quote + citation
|   |   |   |   |-- DimensionScoreBar.tsx     # Visual score bar
|   |   |   |   |-- SourceFilterTabs.tsx      # Rankings, Earnings Calls, Annual Reports, etc.
|   |   |   |
|   |   |   |-- chat/
|   |   |   |   |-- ChatPanel.tsx             # Right-side chat container
|   |   |   |   |-- ChatMessage.tsx           # Message bubble (user/assistant)
|   |   |   |   |-- ChatInput.tsx             # Text input + send
|   |   |   |
|   |   |   |-- common/
|   |   |       |-- LoadingSteps.tsx          # Pipeline progress indicator
|   |   |       |-- CitationLink.tsx          # Clickable source reference
|   |   |       |-- ScoreBadge.tsx            # Colored score display
|   |   |       |-- PersonaBadge.tsx          # Strategic/PE/Conglomerate pill
|   |   |
|   |   |-- hooks/
|   |   |   |-- usePipeline.ts           # Pipeline state, polling/SSE
|   |   |   |-- useChat.ts              # Chat state, message history
|   |   |   |-- useWeights.ts           # Weight slider state, debounced re-score
|   |   |
|   |   |-- lib/
|   |   |   |-- api.ts                  # Fetch wrapper, base URL config
|   |   |   |-- types.ts              # TypeScript interfaces mirroring Pydantic models
|   |   |   |-- constants.ts          # Default weights, persona options
|   |   |
|   |   |-- styles/
|   |       |-- globals.css
|   |
|   |-- package.json
|   |-- tsconfig.json
|   |-- next.config.js
|   |-- Dockerfile
|
|-- docker-compose.yml                  # backend + frontend
|-- Makefile                            # dev shortcuts
|-- README.md
```

---

## 6. Data Models

### 6.1 Target Profile (`models/target.py`)

```python
class TargetProfile(BaseModel):
    company_name: str
    url: str
    description: str                          # 2-3 sentence summary
    sector_l1: str                            # e.g., "Industrials"
    sector_l2: str                            # e.g., "Environmental Services"
    sector_l3: str                            # e.g., "Air Pollution Control"
    key_technologies: list[str]               # e.g., ["ESP", "Flue Gas Treatment"]
    estimated_employees: int | None
    estimated_revenue_usd: str | None         # range, e.g., "30M-50M"
    geographic_footprint: list[str]           # e.g., ["Switzerland", "Germany", "India"]
    years_in_operation: int | None
    india_connection: str | None
    strategic_notes: str                      # what makes this valuable to an acquirer
    raw_scraped_text: str                     # stored for audit trail
```

### 6.2 Prospect (`models/prospect.py`)

```python
class BuyerPersona(str, Enum):
    STRATEGIC = "strategic"
    PRIVATE_EQUITY = "private_equity"
    CONGLOMERATE = "conglomerate"

class Prospect(BaseModel):
    id: str                                   # UUID
    company_name: str
    ticker: str | None                        # None for private companies
    is_listed: bool
    persona: BuyerPersona
    sector: str
    sector_relevance: str                     # "exact_match" | "adjacent" | "tangential"
    product_mix_notes: str
    estimated_revenue_inr_cr: float | None
    estimated_revenue_usd_m: float | None
    website_url: str | None
    source: str                               # "fmp" | "exa" | "claude_search"
    country: str = "India"
```

### 6.3 Signal (`models/signal.py`)

```python
class SignalType(str, Enum):
    ACQUISITION_INTENT = "acquisition_intent"
    SECTOR_EXPANSION = "sector_expansion"
    TECHNOLOGY_GAP = "technology_gap"
    GEOGRAPHIC_INTEREST = "geographic_interest"
    CAPEX_SIGNAL = "capex_signal"
    BOARD_ACTION = "board_action"
    PRODUCT_MIX_MATCH = "product_mix_match"     # for private companies

class SignalStrength(str, Enum):
    HIGH = "high"       # explicit acquisition intent
    MEDIUM = "medium"   # strong indirect indicator
    LOW = "low"         # weak/circumstantial indicator

class Signal(BaseModel):
    id: str
    prospect_id: str
    quote: str                                # exact verbatim quote from source
    signal_type: SignalType
    strength: SignalStrength
    source_document: str                      # e.g., "Q3 FY26 Earnings Call Transcript"
    source_quarter: str                       # e.g., "Q3 FY26"
    source_url: str | None
    reasoning: str                            # why this is relevant to the target
```

### 6.4 Scoring (`models/scoring.py`)

```python
class ScoringWeights(BaseModel):
    sector_adjacency: float = 20.0
    technology_gap: float = 20.0
    geographic_strategy: float = 15.0
    financial_capacity: float = 15.0
    timing_signals: float = 15.0
    product_mix: float = 15.0
    # Validator ensures weights sum to 100

class DimensionScore(BaseModel):
    dimension: str
    score: float                              # 0-10
    weight: float                             # percentage
    justification: str
    supporting_quote: str | None
    source: str | None

class ScoredProspect(BaseModel):
    prospect: Prospect
    signals: list[Signal]
    dimension_scores: list[DimensionScore]
    weighted_total: float                     # 0-100
    rank: int
    top_signal: Signal | None
    match_reasoning: str                      # "Why This Match" summary
```

### 6.5 Pipeline State (`models/pipeline.py`)

```python
class PipelineStatus(str, Enum):
    CREATED = "created"
    PROFILING = "profiling"
    PROFILE_READY = "profile_ready"           # paused -- waiting for user confirmation
    PROSPECTING = "prospecting"
    EXTRACTING_SIGNALS = "extracting_signals"
    SCORING = "scoring"
    COMPLETE = "complete"
    FAILED = "failed"

class UserFilters(BaseModel):
    personas: list[BuyerPersona]
    revenue_min_usd_m: float | None = None
    revenue_max_usd_m: float | None = None
    geography: str = "India"
    custom_signal_keywords: list[str] = []
    num_results: int = 25

class PipelineRun(BaseModel):
    id: str                                   # UUID
    created_at: datetime
    status: PipelineStatus
    target_url: str
    target_profile: TargetProfile | None
    user_filters: UserFilters
    scoring_weights: ScoringWeights
    prospects: list[Prospect] = []
    signals: dict[str, list[Signal]] = {}     # keyed by prospect_id
    scored_prospects: list[ScoredProspect] = []
    error_message: str | None = None
    step_timings: dict[str, float] = {}       # step_name -> seconds elapsed
```

---

## 7. Prompt Chain Architecture

### 7.1 Orchestration Flow

```python
# pipeline_orchestrator.py (simplified)

async def run_pipeline(run_id):

    # Step 1: Target Profiling
    raw_text = await scraper.scrape_url(url)
    profile = await target_profiler.profile_target(raw_text)
    # --> PAUSE: wait for user to confirm/edit via PUT /profile

    # Step 2: Prospect Generation (two parallel tracks)
    listed, private = await asyncio.gather(
        prospect_generator.find_listed(profile, filters),
        prospect_generator.find_private(profile, filters),
    )
    prospects = merge_and_deduplicate(listed, private)

    # Step 3: Signal Extraction (fan-out with concurrency control)
    semaphore = asyncio.Semaphore(10)
    signals = await asyncio.gather(*[
        signal_extractor.extract_for_company(p, profile, keywords, semaphore)
        for p in prospects
    ])

    # Step 4: Scoring (fan-out)
    scored = await asyncio.gather(*[
        scorer.score_single(p, signals[p.id], profile, weights)
        for p in prospects
    ])
    scored.sort(key=lambda x: x.weighted_total, reverse=True)

    # --> COMPLETE: results available for UI + chat
```

### 7.2 Claude Call Specifications

| Step | Model | Max Tokens | Temperature | Response Format |
|------|-------|-----------|-------------|-----------------|
| Step 1: Profiling | claude-sonnet | 2048 | 0.0 | JSON |
| Step 2: Prospect Classification | claude-sonnet | 4096 | 0.2 | JSON array |
| Step 2: Private Discovery | claude-sonnet | 4096 | 0.3 | JSON array |
| Step 3: Signal Extraction | claude-sonnet | 2048 | 0.0 | JSON array |
| Step 4: Scoring | claude-sonnet | 2048 | 0.0 | JSON |
| Step 5: Chat | claude-sonnet | 4096 | 0.4 | Markdown |

### 7.3 Prompt Templates (Summary)

**Step 1 -- Target Profiling Prompt:**
- Input: scraped website text
- Role: "You are an M&A analyst"
- Extracts: company name, description, 3-level sector, technologies, size, geography, strategic notes
- Output: Structured JSON

**Step 2 -- Prospect Generation Prompt:**
- Input: target profile JSON + user filters (persona, revenue, geography)
- Role: "You are an M&A analyst building a buyer prospect list"
- Classifies: persona type, sector relevance, product mix fit, revenue estimate
- Sorting: Strategic buyers first, then PE, then Conglomerates (unless direct signal match)
- Output: JSON array of prospects

**Step 3 -- Signal Extraction Prompt:**
- Input: transcript text + target profile + company name + quarter + custom keywords
- Role: "You are an M&A intelligence analyst"
- Looks for: acquisition intent, sector expansion, technology gaps, geographic interest, capex signals, board actions
- Extracts: exact quote, signal type, strength, reasoning
- Critical instruction: "Do not fabricate signals"
- Output: JSON array of signals

**Step 4 -- Scoring Prompt:**
- Input: target profile + buyer profile + buyer signals + 6 dimension weights
- Role: "You are an M&A matching engine"
- Scores: 6 dimensions (0-10 each) with justification and supporting quote
- Output: JSON with dimension scores and weighted total

**Step 5 -- Chat System Prompt:**
- Context: target profile + scored prospects + all signals (injected as system context)
- Role: "You are an M&A intelligence assistant"
- Capabilities: explain rankings, show quotes, accept new signals, answer strategic questions
- Critical instruction: "Never fabricate information. Always cite sources."

---

## 8. API Endpoint Design

### 8.1 Pipeline Lifecycle

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| `POST` | `/api/v1/pipeline/run` | Create run, start Step 1 | `{url, filters, weights}` | `{run_id, status}` |
| `GET` | `/api/v1/pipeline/{run_id}` | Get full pipeline state | -- | `PipelineRun` |
| `GET` | `/api/v1/pipeline/{run_id}/status` | Lightweight status check | -- | `{status, step, progress_pct}` |
| `PUT` | `/api/v1/pipeline/{run_id}/profile` | Confirm/edit profile, trigger Step 2 | `TargetProfile` | `{status}` |
| `POST` | `/api/v1/pipeline/{run_id}/rescore` | Re-run Step 4 with new weights | `ScoringWeights` | `{status}` |

### 8.2 Results

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/pipeline/{run_id}/prospects` | Scored & ranked prospect list |
| `GET` | `/api/v1/pipeline/{run_id}/prospects/{prospect_id}` | Single prospect with all details |
| `GET` | `/api/v1/pipeline/{run_id}/signals` | All signals (filterable: `?type=`, `?strength=`) |
| `GET` | `/api/v1/pipeline/{run_id}/export` | CSV/Excel download |

### 8.3 Chat

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/pipeline/{run_id}/chat` | Send message, get response |
| `GET` | `/api/v1/pipeline/{run_id}/chat/history` | Get chat history |

### 8.4 Live Progress (Server-Sent Events)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/pipeline/{run_id}/events` | SSE stream of pipeline progress |

Events emitted: `profile_complete`, `prospects_found`, `transcript_processed` (per company), `signals_extracted`, `scoring_complete`, `pipeline_complete`, `pipeline_error`.

---

## 9. Frontend Component Hierarchy

```
App (layout.tsx)
|
|-- Sidebar
|   |-- NavItem: "Prospecting" (active)
|   |-- NavItem: "Buy-Side" (disabled, "Coming Soon")
|
|-- MainLayout (three columns)
    |
    |-- Center Panel (columns 1+2)
    |   |
    |   |-- [Before run] TargetInputForm
    |   |   |-- URL text input + "Analyse" button
    |   |   |
    |   |   |-- [After Step 1] TargetProfileCard (editable)
    |   |   |   |-- Company name, description, sector breadcrumb
    |   |   |   |-- Technologies, size, geography
    |   |   |   |-- "Confirm & Find Buyers" button
    |   |   |
    |   |   |-- [After confirm] Filter controls
    |   |       |-- PersonaCheckboxes
    |   |       |-- RevenueRangeSlider
    |   |       |-- NumResultsDropdown
    |   |       |-- CustomKeywordsInput
    |   |       |-- WeightSliders (6 dimensions)
    |   |
    |   |-- [During pipeline] LoadingSteps
    |   |   |-- "Analyzing target... Finding buyers..."
    |   |   |-- "Extracting signals (12/47)... Scoring..."
    |   |
    |   |-- [After complete] Results View
    |       |-- ResultsSummaryBar
    |       |   |-- Total Matches | Strong Signals | Avg Score | Sources Scanned
    |       |
    |       |-- SourceFilterTabs
    |       |
    |       |-- ResultsTable
    |           |-- ProspectRow (expandable, repeated)
    |               |-- Rank | Company | Persona | Sector | Revenue | Score | Signal | Source
    |               |
    |               |-- [Expanded] ExpandedProspect
    |                   |-- Acquisition Signals -> SignalCard (repeated)
    |                   |-- Why This Match -> reasoning text
    |                   |-- Dimension Scores -> DimensionScoreBar (x6)
    |                   |-- Actions: "Add to shortlist" | "View full profile" | "Generate teaser"
    |
    |-- Right Panel
        |-- ChatPanel
            |-- Message list (scrollable) -> ChatMessage (repeated)
            |-- ChatInput -> text input + send button
```

### State Management

| Hook | Responsibility |
|------|---------------|
| `usePipeline` | Pipeline run state, polling/SSE, status transitions |
| `useWeights` | Weight slider values, debounced re-score API calls |
| `useChat` | Message history, send/receive, streaming display |

---

## 10. Phase Breakdown & Milestones

### Phase 0: Project Scaffolding (Days 1-2)

**Goal:** "Hello World" end-to-end.

| Task | Details |
|------|---------|
| Initialize monorepo | `pyproject.toml` (fastapi, uvicorn, anthropic, httpx, beautifulsoup4, pydantic, aiosqlite) + Next.js + Tailwind |
| FastAPI skeleton | `/health` endpoint, CORS, config from env vars |
| Anthropic client | Thin wrapper with test call to verify API key |
| Frontend shell | Three-column layout (sidebar + center + right panel) |
| Docker Compose | Local dev environment |

**Exit criteria:** `/health` returns 200. Frontend renders layout. Claude responds to test prompt.

---

### Phase 1: Target Company Profiling (Days 3-6)

**Goal:** User pastes a URL, sees a structured company profile.

| Task | Details |
|------|---------|
| `scraper.py` | `scrape_url(url) -> str` -- httpx + BeautifulSoup, strip nav/footer/scripts |
| `target_profiler.py` | `profile_target(scraped_text) -> TargetProfile` -- Claude call + JSON parse |
| Profiling prompt | Template with JSON schema instruction in `prompts/target_profiling.py` |
| Pipeline model | `PipelineRun` state object, persisted to SQLite |
| API routes | `POST /target/profile` (start), `PUT /target/{run_id}/profile` (edit/confirm) |
| `TargetInputForm.tsx` | URL input + "Analyse" button |
| `TargetProfileCard.tsx` | Editable profile display with "Confirm & Find Buyers" button |
| `LoadingSteps.tsx` | Step 1 progress indicator |

**Exit criteria:** Entering `https://www.elex.ch/en/` produces a correct structured profile. User can edit sector and confirm.

---

### Phase 2: Prospect List Generation (Days 7-11)

**Goal:** Confirmed profile produces 25-50 Indian buyer prospects.

| Task | Details |
|------|---------|
| `fmp_client.py` | `search_companies_by_sector()` -- FMP stock screener / company search |
| `exa_client.py` | `search_companies(query, geography)` -- Exa semantic search |
| `prospect_generator.py` | Two parallel tracks via `asyncio.gather()`: listed (FMP+Exa+Claude) and private (Exa+Claude) |
| Prospect prompts | Classification prompt for listed, discovery prompt for private |
| Prospect model | `Prospect` Pydantic model with persona, sector relevance, revenue |
| Filter UI | Persona multi-select, revenue range, number of results |

**Exit criteria:** For elex.ch, system returns recognizable names (Thermax, Ion Exchange, etc.) plus private company discoveries.

---

### Phase 3: Signal Extraction (Days 12-18)

**Goal:** Each listed prospect has acquisition signals with exact quotes from earnings transcripts.

| Task | Details |
|------|---------|
| `fmp_client.py` extended | `get_earnings_transcripts(ticker, last_n_quarters=4)` -- handle Indian tickers |
| `signal_extractor.py` | Fan-out with `asyncio.Semaphore(10)` for rate limiting |
| Signal extraction prompt | Per-transcript prompt with target context + custom keywords |
| Signal model | `Signal` with quote, type, strength, source, reasoning |
| Cache layer | `cache_manager.py` -- cache transcripts by `{ticker}:{quarter}` (they never change) |
| Text processing utils | Transcript chunking if exceeding context window |
| Private company signals | Profile-based signals (sector match, product mix) |
| Keyword pre-filter | Regex scan before Claude call to skip irrelevant transcripts |

**Exit criteria:** Thermax shows real quotes about inorganic growth. At least 3-5 companies have high-strength signals. Zero fabricated quotes.

**Note:** This is the most implementation-intensive phase. Budget extra time for FMP Indian ticker format, rate limiting, and prompt iteration.

---

### Phase 4: Scoring & Ranking (Days 19-22)

**Goal:** Prospects scored across 6 dimensions, ranked, and displayed in the results table.

| Task | Details |
|------|---------|
| `scorer.py` | Fan-out scoring calls via `asyncio.gather()` |
| Scoring prompt | 6-dimension weighted scoring with justification + supporting quotes |
| Scoring model | `DimensionScore`, `ScoredProspect`, `ScoringWeights` |
| Re-score endpoint | `POST /rescore` -- re-runs only Step 4 (not Steps 1-3) |
| `ResultsSummaryBar.tsx` | 4 stat cards: Total Matches, Strong Signals, Avg Score, Sources Scanned |
| `ResultsTable.tsx` | Ranked table: Rank, Company, Persona, Sector, Revenue, Score, Signal, Source |
| `ProspectRow.tsx` | Expandable row |
| `ExpandedProspect.tsx` | All signals (SignalCard), 6 dimension scores (DimensionScoreBar), reasoning |
| `WeightSliders.tsx` | 6 sliders with debounced re-score on change |
| `SourceFilterTabs.tsx` | Rankings, Earnings Calls, Annual Reports, SEBI Filings tabs |

**Exit criteria:** Full pipeline runs end-to-end. elex.ch produces 15-20 ranked companies. Adjusting weights re-ranks in real-time.

---

### Phase 5: Chat Interface (Days 23-27)

**Goal:** User can interrogate results conversationally.

| Task | Details |
|------|---------|
| `chat_service.py` | Context assembly (target + prospects + signals) -> Claude call with conversation history |
| Chat system prompt | Injected full pipeline output as context |
| Context management | Summarize lower-ranked prospects if context exceeds limits |
| `POST /chat` | Request/response endpoint (optionally streaming) |
| `ChatPanel.tsx` | Right sidebar with scrollable message history |
| `ChatMessage.tsx` | User/assistant bubbles with markdown + citation rendering |
| `ChatInput.tsx` | Text input + send |
| `useChat.ts` | Hook: message history, optimistic UI, streaming |

**Exit criteria:** "Why is Thermax ranked #1?" returns a detailed answer citing specific transcript quotes.

---

### Phase 6: Polish & Demo Prep (Days 28-32)

| Task | Details |
|------|---------|
| Error handling | Graceful degradation (FMP down, transcript not found, Claude timeout) |
| Pipeline resilience | Resume from last completed step on failure |
| Loading states | Skeleton screens, error toasts, progress bars |
| Export | CSV/Excel download of results |
| Performance | Target < 10 minutes end-to-end for 20 companies |
| Prompt eval suite | 20 manually-labeled transcripts, automated accuracy tests |
| Documentation | README, setup instructions, env var documentation |

---

## 11. Build Order & Dependency Graph

The critical path is: **Scaffolding -> Step 1 -> Step 2 -> Step 3 -> Step 4 -> Results UI -> Chat**.

Steps 1-4 must be built sequentially on the backend (each feeds into the next). Frontend work can be parallelized if there are two developers.

### Single-Developer Weekly Schedule

```
Week 1:  Scaffolding + Step 1 backend + Step 1 frontend (profile input/display)
Week 2:  Step 2 backend (prospects) + Step 3 backend (signals)
Week 3:  Step 4 backend (scoring) + Results UI (table, rows, signals, scores)
Week 4:  Chat backend + Chat UI + Weight sliders reactivity + Polish
Week 5:  Testing, prompt tuning, performance optimization, demo prep
```

### Exact Build Sequence (file by file)

| Order | File | Depends On |
|-------|------|-----------|
| 1 | `config.py` + `main.py` + `dependencies.py` | -- |
| 2 | `clients/anthropic_client.py` | config |
| 3 | `models/target.py` + `models/pipeline.py` | -- |
| 4 | `clients/scraper.py` | -- |
| 5 | `prompts/target_profiling.py` + `services/target_profiler.py` | 2, 3, 4 |
| 6 | `routers/pipeline.py` (initial) | 5 |
| 7 | Frontend: layout + `TargetInputForm` + `TargetProfileCard` | 6 |
| 8 | `clients/fmp_client.py` + `clients/exa_client.py` | config |
| 9 | `prompts/prospect_generation.py` + `services/prospect_generator.py` | 5, 8 |
| 10 | `models/signal.py` | -- |
| 11 | `cache/cache_manager.py` | -- |
| 12 | `prompts/signal_extraction.py` + `services/signal_extractor.py` | 8, 10, 11 |
| 13 | `models/scoring.py` | 10 |
| 14 | `prompts/scoring.py` + `services/scorer.py` | 12, 13 |
| 15 | `services/pipeline_orchestrator.py` | 5, 9, 12, 14 |
| 16 | Frontend: results components | 15 |
| 17 | `hooks/usePipeline.ts` | 16 |
| 18 | `WeightSliders.tsx` + `hooks/useWeights.ts` | 17 |
| 19 | `services/chat_service.py` + `prompts/chat.py` + `routers/chat.py` | 15 |
| 20 | Frontend: chat components + `hooks/useChat.ts` | 19 |

---

## 12. Cost Analysis

### Per-Pipeline-Run Cost (Claude API)

| Step | Input Tokens | Output Tokens | Sonnet Cost |
|------|-------------|--------------|-------------|
| Step 1: Profiling | ~10K (scraped page) | ~500 | ~$0.03 |
| Step 2: Prospects | ~5K | ~2K | ~$0.02 |
| Step 3: Signals (80 transcripts) | ~1.2M (15K x 80) | ~40K | ~$3.60 |
| Step 4: Scoring (25 prospects) | ~50K | ~12K | ~$0.20 |
| Step 5: Chat (per message) | ~20K (context) | ~1K | ~$0.06 |
| **Total per run** | | | **~$4-6** |

### Cost Optimization Strategies

1. **Pre-filter transcripts** with keyword regex before sending to Claude -- eliminates 50-70% of calls
2. **Cache aggressively** -- same transcript + same target profile = same signals
3. **Batch API** for background pre-processing (50% cost reduction, 24h latency)
4. **Summarize context** for chat -- top 10 full detail, rest summarized

---

## 13. Risk Areas & Mitigations

### Risk 1: FMP API Indian Ticker Coverage

**Risk:** FMP may not have comprehensive coverage of BSE/NSE tickers.
**Mitigation:** Test on day 7 (Phase 2). If coverage is poor, fall back to Exa API for discovery + Claude for profile extraction from company websites. Architecture already has two tracks (listed + private).

### Risk 2: Signal Extraction Hallucination

**Risk:** Claude fabricates quotes not present in the transcript.
**Mitigation:**
- Set temperature to 0.0 for signal extraction
- Post-processing validation: fuzzy-match returned quotes against input transcript text
- Discard/flag signals where quote cannot be verified
- Build eval suite of 20 manually-labeled transcripts early

### Risk 3: Pipeline Exceeds 10-Minute Target

**Risk:** 80 transcript Claude calls at ~3s each = 4 min parallelized. Add FMP fetch latency.
**Mitigation:**
- Pre-filter transcripts with keyword scan (skip ~60% of Claude calls)
- Increase concurrency semaphore
- Show partial results via SSE as they arrive (perceived progress)

### Risk 4: Context Window Limits for Chat

**Risk:** Full pipeline output (20+ prospects x signals x scores) exceeds context limits.
**Mitigation:** Include full detail for top 10 prospects, summarize the rest. Fetch full detail on demand when user asks about a lower-ranked prospect.

### Risk 5: Prompt Quality Regression

**Risk:** Prompt changes improve one case but break another.
**Mitigation:** Build eval suite (20 labeled transcripts) before shipping. Run automated tests on every prompt change. Treat prompt changes like code changes -- test before deploying.

---

## 14. Architectural Decisions & Trade-offs

| Decision | Rationale |
|----------|-----------|
| **No LangChain/LangGraph** | Pipeline is linear with simple fan-out. `asyncio.gather()` handles it. Framework would obscure prompt logic (which IS the product). |
| **SQLite over PostgreSQL** | Single-user demo. No concurrent writes. Zero-config. Easy migration to Postgres later via SQLAlchemy. |
| **SSE over WebSocket for progress** | Unidirectional, works through proxies, auto-reconnects. Pipeline only pushes events. |
| **Sonnet over Haiku for signals** | Signal extraction requires contextual understanding. Haiku risks higher false-positives. Cost difference (~$2/run) acceptable for quality. |
| **Pause after Step 1** | User must confirm/edit profile before it drives the rest of the pipeline. Misclassified sector cascades errors through all steps. |
| **Prompts as plain Python strings** | Maximum visibility and control. Easy to iterate, test, and version. No template engine overhead. |

---

## 15. MVP Scope vs Future Versions

### In Scope (MVP / V1)

- Sell-side prospecting only
- 5-step prompt chain (profile -> prospect -> signals -> score -> chat)
- India geography only
- FMP transcripts + Exa company discovery
- SaaS dashboard UI with results table + chat
- Configurable weights and filters
- Full citation trail

### Out of Scope (Future Versions)

| Feature | Version | Notes |
|---------|---------|-------|
| Buy-side mandates | V2 | Greyed out in sidebar |
| Deal comparables & valuation benchmarks | V2 | Comparable transactions, regulatory considerations |
| Deal Tracker (Kanban) | V2 | Identified -> Approached -> In Discussion -> LOI |
| Geography expansion | V2 | Beyond India |
| Chat-first interface | V2 | Full conversational UI |
| SEBI disclosure scraping | V1.5 | Board resolutions, acquisition filings |
| Annual report parsing | V1.5 | Investor presentations, capex guidance |
| Multi-user & authentication | V2 | Team access, role-based permissions |
| Export to pitch deck | V2 | Generate teaser documents |

---

## Key Design Principles

1. **Claude is the engine, not the database.** Every analytical step is a Claude prompt. Backend orchestrates prompts, manages variables, caches results, serves UI. Keep the backend thin.

2. **Every output must be cited.** If a signal is shown, the user must be able to trace it to the exact source -- transcript name, quarter, verbatim quote. No black box.

3. **User variables drive the prompts.** When the user changes a filter or weight, the relevant prompt re-runs. Make this reactive.

4. **Prompt design is product design.** Build an eval set. Test prompts against it. Iterate on prompts like you iterate on UI.
