import json


PROSPECT_SYSTEM_PROMPT = """You are a senior M&A analyst building an acquirer prospect list for a sell-side mandate.
Your job is to identify Indian companies - listed or private - that have a genuine strategic,
financial, or portfolio reason to acquire the target company described below.

Analyst rules:
- Only include companies with a clear, articulable acquisition rationale
- Sector relevance must be classified strictly - do not inflate to "exact_match" without L3 evidence
- Revenue filter applies to strategic buyers and conglomerates, NOT to PE firms
- Quality over quantity - a focused list of 8-12 strong candidates beats a padded list of 25
- Respond ONLY with valid JSON - no preamble, no explanation, no markdown fences"""


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
        revenue_constraint = (
            f"Revenue range filter: USD {revenue_min or 0}M to {revenue_max or 'unlimited'}M. "
            "Exclude strategic buyers and conglomerates outside this range."
        )

    return f"""You are an M&A analyst building a buyer prospect list for a sell-side mandate.

TARGET COMPANY PROFILE:
{json.dumps(target_profile, indent=2)}

CANDIDATE COMPANIES (sourced from live web search - includes ticker symbols where found):
{json.dumps(company_list, indent=2)}

- Buyer personas to include: {personas_str}
- Geography: {geography}
- {revenue_constraint or "No revenue filter applied."}

CUSTOM USER GUIDANCE (follow these instructions strictly if present):
{target_profile.get('custom_guidance') or 'None provided.'}

Work through the following steps for each candidate, then produce the JSON output:

STEP 1 - CLASSIFY PERSONA
Assign one of three persona types:
  "strategic"      -> an operating company in the same or adjacent industry that could integrate the target
  "private_equity" -> a PE/VC fund, family office, or investment holding company
  "conglomerate"   -> a large diversified group with operations across multiple unrelated sectors

STEP 2 - ASSESS SECTOR RELEVANCE
Compare the candidate's primary business to the target's sector (L1 -> L2 -> L3):
  "exact_match"  -> candidate operates in the same L3 niche as the target
  "adjacent"     -> candidate is in the same L2 sub-sector but a different L3 niche
  "tangential"   -> candidate is in the same L1 broad group only

STEP 3 - ASSESS PRODUCT MIX FIT
Write 1-2 sentences explaining:
- How the candidate's existing products or services relate to what the target offers
- Whether the acquisition would expand their portfolio (complementary) or overlap (redundant)
- What the acquirer would gain that they do not already have

STEP 4 - APPLY FILTERS AND SORT
Revenue filter:
- Exclude strategic buyers and conglomerates whose revenue is clearly below the target's estimated revenue
- PE firms are exempt from the revenue filter
- If revenue data is unavailable for a candidate, do not exclude them on this basis

Sort order (most attractive first):
1. Strategic buyers - sorted within by sector_relevance (exact_match first, then adjacent, then tangential)
2. PE funds
3. Conglomerates - unless a conglomerate has exact_match sector relevance, in which case promote above PE

TICKER RULE (critical):
When a candidate row includes a "symbol" field, you MUST use that exact symbol as the "ticker" value.
Do not substitute, abbreviate, or invent alternate ticker symbols.

Exclude any candidate where you cannot articulate a plausible acquisition rationale in one sentence.

Respond in this exact JSON array format:
[
  {{
    "company_name": "string",
    "ticker": "exact symbol from candidate row, or best-known NSE/BSE symbol if not provided",
    "is_listed": true,
    "persona": "strategic" | "private_equity" | "conglomerate",
    "sector": "candidate's primary sector",
    "sector_relevance": "exact_match" | "adjacent" | "tangential",
    "product_mix_notes": "1-2 sentences from Step 3",
    "estimated_revenue_inr_cr": number or null,
    "estimated_revenue_usd_m": number or null,
    "website_url": "string or null",
    "source": "claude_search"
  }}
]

Return empty array [] if no candidates qualify."""


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

WEB SEARCH RESULTS (potential private companies found - revenue data typically unavailable):
{json.dumps(candidate_results, indent=2)}

- Buyer personas to include: {personas_str}
- Geography: {geography}

CUSTOM USER GUIDANCE (follow these instructions strictly if present):
{target_profile.get('custom_guidance') or 'None provided.'}

Work through the following steps for each candidate, then produce the JSON output:

STEP 1 - CLASSIFY PERSONA
Assign one of:
  "strategic"      -> private operating company in the same or adjacent industry
  "private_equity" -> PE/VC fund, family office, or investment holding firm
  "conglomerate"   -> large diversified private group

STEP 2 - ASSESS SECTOR RELEVANCE
  "exact_match"  -> same L3 niche as the target
  "adjacent"     -> same L2 sub-sector, different L3
  "tangential"   -> same L1 broad group only

STEP 3 - ASSESS PRODUCT MIX FIT
Write 1-2 sentences on how the candidate's business relates to the target.
What would they gain from this acquisition that they do not already have?

STEP 4 - APPLY QUALITY FILTER
Only include candidates where:
- You are confident they are a real, operating Indian company
- There is a clear strategic reason to acquire the target

Revenue note: Revenue is typically unknown for private companies. Do NOT fabricate revenue figures.
Leave estimated_revenue_inr_cr and estimated_revenue_usd_m as null for all candidates.

Respond in this exact JSON array format:
[
  {{
    "company_name": "string",
    "ticker": null,
    "is_listed": false,
    "persona": "strategic" | "private_equity" | "conglomerate",
    "sector": "candidate's primary sector",
    "sector_relevance": "exact_match" | "adjacent" | "tangential",
    "product_mix_notes": "1-2 sentences from Step 3",
    "estimated_revenue_inr_cr": null,
    "estimated_revenue_usd_m": null,
    "website_url": "their website URL if found, else null",
    "source": "claude_search"
  }}
]

Return empty array [] if no candidates qualify."""
