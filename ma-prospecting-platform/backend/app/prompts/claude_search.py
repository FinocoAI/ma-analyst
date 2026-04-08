import json


PROFILE_ENRICHMENT_SYSTEM_PROMPT = """You are a company research analyst.
Use the web_search tool to retrieve live information before answering.
Do not rely on memory for factual company details.
Return plain text only."""

LISTED_CANDIDATES_SYSTEM_PROMPT = """You are an M&A analyst specializing in Indian listed companies.
Use the web_search tool to find real, currently listed Indian companies on NSE or BSE.
Verify companies through live search results before including them.
Return only valid JSON."""

PRIVATE_CANDIDATES_SYSTEM_PROMPT = """You are an M&A analyst specializing in Indian private companies.
Use the web_search tool to find real, unlisted Indian companies that are plausible acquirers.
Return only valid JSON."""

TICKER_RESOLUTION_SYSTEM_PROMPT = """You are a financial data assistant.
Use the web_search tool to find the current NSE or BSE ticker for an Indian listed company.
Verify the symbol from live search results and return only valid JSON."""

TRANSCRIPT_METADATA_SYSTEM_PROMPT = """You are a financial analyst.
You will be given raw text scraped from a public web page or PDF.
Identify whether the text contains an actual earnings call transcript for the named company.
Return only valid JSON."""

MA_PRESS_SYSTEM_PROMPT = """You are an M&A research analyst.
Use the web_search tool to find recent, real, sourced mentions of acquisitions, inorganic growth,
or management commentary on M&A strategy for the named company.
Do not use memory. Return plain text only."""


def build_profile_enrichment_prompt(url: str, thin_text: str) -> str:
    return f"""URL: {url}

Thin scraped text (may be incomplete):
{thin_text[:3000]}

Use live web search to identify the company behind this URL and write a rich plain-text profile.
Include:
- what the company does
- products and services
- key end markets and geographies
- approximate size or scale if available
- strategic context relevant to an M&A analyst

Return plain text only."""


def build_listed_candidates_prompt(
    target_profile: dict,
    filters: dict,
    budget: int,
) -> str:
    return f"""Target company profile:
{json.dumps(target_profile, indent=2)}

Filters:
- Geography: {filters.get("geography", "India")}
- Buyer personas: {", ".join(filters.get("personas", []))}
- Revenue range: {filters.get("revenue_min_usd_m")} to {filters.get("revenue_max_usd_m")} USD million

Find up to {budget} real Indian listed companies on NSE or BSE that could plausibly acquire this target.
For each company return:
[
  {{
    "company_name": "string",
    "symbol": "canonical ticker symbol",
    "exchange": "NSE" or "BSE" or "",
    "estimated_revenue_usd_m": number or null,
    "sector": "string",
    "url": "company or source URL if available",
    "description": "brief description",
    "source": "claude_search"
  }}
]

Requirements:
- Verify each company exists and is currently listed
- Prefer strategic buyers, but include PE or conglomerates when plausible
- Exclude obvious mismatches
- Return JSON array only"""


def build_private_candidates_prompt(
    target_profile: dict,
    filters: dict,
    budget: int,
) -> str:
    return f"""Target company profile:
{json.dumps(target_profile, indent=2)}

Filters:
- Geography: {filters.get("geography", "India")}
- Buyer personas: {", ".join(filters.get("personas", []))}

Find up to {budget} real Indian private or unlisted companies that could plausibly acquire this target.
For each company return:
[
  {{
    "title": "company name",
    "url": "company website or source URL",
    "snippet": "brief description and why it is a candidate"
  }}
]

Requirements:
- Only include real Indian companies you can verify through live search
- Prefer same-sector or adjacent strategic buyers
- Return JSON array only"""


def build_ticker_resolution_prompt(company_name: str, ticker_hint: str | None) -> str:
    return f"""Company name: {company_name}
Ticker hint: {ticker_hint or "none"}

Search for the current canonical NSE ticker for this company.
If the company is only listed on BSE, return the BSE code instead.
Return JSON only in this shape:
{{"ticker": "SYMBOL"}} or {{"ticker": null}}"""


def build_transcript_metadata_prompt(
    company_name: str,
    ticker: str,
    source_url: str,
    scraped_text: str,
) -> str:
    return f"""Company: {company_name} (Ticker: {ticker})
Source URL: {source_url}

Scraped text:
{scraped_text[:40000]}

Determine whether this source contains an actual earnings call transcript for the named company.
Return a JSON array. For each transcript detected, return:
[
  {{
    "quarter": 1,
    "year": 2025,
    "date": "YYYY-MM-DD or empty string"
  }}
]

Rules:
- Return [] if the source is only a transcript listing page, investor presentation, or unrelated document
- Infer quarter only when the text clearly supports it
- Return JSON array only"""


def build_ma_press_prompt(company_name: str, ticker: str | None, target_profile: dict) -> str:
    return f"""Company: {company_name} (Ticker: {ticker or "unlisted"})

Target company context:
{json.dumps(target_profile, indent=2)}

Search the last 2 years for:
- acquisitions made or announced by this company
- management commentary about inorganic growth or M&A strategy
- investor relations or earnings-call commentary about acquisitions

Return relevant excerpts as plain text with source URLs.
If nothing relevant is found, return exactly: NO_RESULTS"""
