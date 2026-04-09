import json

PROSPECT_SYSTEM_PROMPT = """You are a senior M&A analyst building a buyer prospect list for a sell-side mandate.
You understand the Indian corporate landscape, listed companies, PE funds, and conglomerates.
Respond ONLY with valid JSON - no preamble, no explanation."""


def build_listed_prospect_prompt(
    target_profile: dict,
    company_list: list[dict],
    personas: list[str],
    revenue_min: float | None,
    revenue_max: float | None,
    geography: str = "India",
) -> str:
    personas_str = ", ".join(personas)
    revenue_constraint = ""
    if revenue_min or revenue_max:
        revenue_constraint = f"Revenue range filter: {revenue_min or 0} to {revenue_max or 'unlimited'} USD million."

    return f"""You are an M&A analyst building a buyer prospect list for a sell-side mandate.

TARGET COMPANY PROFILE:
{json.dumps(target_profile, indent=2)}

CANDIDATE COMPANIES (from live web search):
{json.dumps(company_list, indent=2)}

- Buyer personas to include: {personas_str}
- Geography: {geography}
- {revenue_constraint}

CUSTOM USER GUIDANCE (Follow these instructions strictly):
{target_profile.get('custom_guidance') or 'None provided.'}

For each company that is a plausible buyer, produce an entry in this JSON array format:
[
  {{
    "company_name": "string",
    "ticker": "exact symbol from the candidate row when provided; else best-known NSE/BSE symbol",
    "is_listed": true,
    "persona": "strategic" | "private_equity" | "conglomerate",
    "sector": "company's primary sector",
    "sector_relevance": "exact_match" | "adjacent" | "tangential",
    "product_mix_notes": "1-2 sentences on how their products relate to the target",
    "estimated_revenue_inr_cr": number or null,
    "estimated_revenue_usd_m": number or null,
    "website_url": "string or null",
    "source": "claude_search"
  }}
]

Rules:
- ONLY include companies that could plausibly want to acquire the target
- TICKER: When a candidate row includes "symbol", you MUST use that exact symbol as "ticker". Do not invent alternate tickers.
- Exclude companies whose revenue is LESS than the target company's revenue (Exception: Do not apply this rule to Private Equity firms, as they do not report traditional corporate revenue)
- Rank: Strategic buyers first, then PE funds, then Conglomerates (unless conglomerate has direct sector match)
- sector_relevance "exact_match" = operates in the same L3 niche; "adjacent" = same L2; "tangential" = same L1 only
- If a company clearly does not fit, exclude it - quality over quantity
- Return empty array [] if no companies qualify"""


def build_private_prospect_prompt(
    target_profile: dict,
    candidate_results: list[dict],
    personas: list[str],
    geography: str = "India",
) -> str:
    personas_str = ", ".join(personas)

    return f"""You are an M&A analyst identifying private Indian companies that could acquire the following target.

TARGET COMPANY PROFILE:
{json.dumps(target_profile, indent=2)}

WEB SEARCH RESULTS (potential private companies found):
{json.dumps(candidate_results, indent=2)}

- Buyer personas to include: {personas_str}
- Geography: {geography}

CUSTOM USER GUIDANCE (Follow these instructions strictly):
{target_profile.get('custom_guidance') or 'None provided.'}

For each private company that is a plausible buyer, produce an entry in this JSON array:
[
  {{
    "company_name": "string",
    "ticker": null,
    "is_listed": false,
    "persona": "strategic" | "private_equity" | "conglomerate",
    "sector": "company's primary sector",
    "sector_relevance": "exact_match" | "adjacent" | "tangential",
    "product_mix_notes": "1-2 sentences on how their products relate to the target",
    "estimated_revenue_inr_cr": null,
    "estimated_revenue_usd_m": null,
    "website_url": "their website URL",
    "source": "claude_search"
  }}
]

Rules:
- Only include companies with a clear strategic reason to acquire the target
- Focus on companies with similar or complementary product mix
- Do NOT include companies you are not confident are real Indian companies
- Return empty array [] if no results qualify"""
