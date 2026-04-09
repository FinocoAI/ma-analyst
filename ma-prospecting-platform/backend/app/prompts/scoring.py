import json


SCORING_SYSTEM_PROMPT = """You are a senior M&A analyst scoring potential acquirers against a target company.
Your role is to evaluate fit across six dimensions using the evidence provided - signals, profiles, and product descriptions.
Every score must be evidence-backed. When signals are used, cite the specific source document.
Respond ONLY with valid JSON - no preamble, no explanation, no markdown fences."""


def build_scoring_prompt(
    target_profile: dict,
    buyer_profile: dict,
    signals: list[dict],
    weights: dict,
) -> str:
    w_sector = weights.get("sector_adjacency", 20)
    w_tech = weights.get("technology_gap", 20)
    w_geo = weights.get("geographic_strategy", 15)
    w_fin = weights.get("financial_capacity", 15)
    w_timing = weights.get("timing_signals", 15)
    w_product = weights.get("product_mix", 15)

    return f"""You are an M&A analyst. Score the potential buyer against the target company
across 6 dimensions using the evidence below. Read the scoring instructions carefully
before assigning any scores.

TARGET COMPANY:
{json.dumps(target_profile, indent=2)}

CUSTOM USER GUIDANCE (adjust scores and reasoning to honor this when relevant):
{target_profile.get('custom_guidance') or 'None provided.'}

POTENTIAL BUYER:
{json.dumps(buyer_profile, indent=2)}

ACQUISITION SIGNALS FOUND FOR THIS BUYER:
{json.dumps(signals, indent=2) if signals else "No signals found from any transcripts or press material."}

SCORING WEIGHTS:
  sector_adjacency:    {w_sector}%
  technology_gap:      {w_tech}%
  geographic_strategy: {w_geo}%
  financial_capacity:  {w_fin}%
  timing_signals:      {w_timing}%
  product_mix:         {w_product}%

SCORING INSTRUCTIONS - read before scoring each dimension:

1. SECTOR ADJACENCY (weight: {w_sector}%)
   How closely does the buyer's primary business overlap with the target's sector?
   - 9-10: Buyer operates in the exact same L3 niche as the target
   - 7-8:  Buyer is in the same L2 sub-sector (adjacent, complementary niche)
   - 4-6:  Buyer is in the same L1 broad group only (tangential connection)
   - 0-3:  Buyer is in an unrelated sector

2. TECHNOLOGY GAP (weight: {w_tech}%)
   Does the buyer lack capabilities that the target provides, creating acquisition pull?
   - 9-10: Buyer has explicitly acknowledged lacking the target's core technology, OR
           their product line has an obvious gap the target fills
   - 6-8:  Clear complementarity - target adds significant capability the buyer lacks
   - 3-5:  Partial overlap - target adds incremental rather than transformational capability
   - 0-2:  Buyer already has equivalent technology, or the target's tech is irrelevant to them

3. GEOGRAPHIC STRATEGY (weight: {w_geo}%)
   Does the buyer have a strategic interest in the target's geographic market?
   - 9-10: Buyer has explicitly expressed interest in entering the target's specific country/region
   - 6-8:  Buyer has signalled international or cross-border expansion intent (geography not yet specified)
   - 3-5:  Buyer has some international presence but no stated interest in the target's region
   - 0-2:  Buyer is entirely focused on domestic market with no stated international ambitions

4. FINANCIAL CAPACITY (weight: {w_fin}%)
   Does the buyer have the financial strength to execute a cross-border acquisition of this size?
   - 9-10: Revenue is >5x the target's estimated revenue AND buyer has prior cross-border deal history
   - 6-8:  Revenue is >2x the target AND balance sheet appears healthy (no debt distress signals)
   - 3-5:  Revenue is comparable to the target - deal is possible but would be a financial stretch
   - 0-2:  Revenue is below the target, OR buyer shows signs of financial stress

5. TIMING SIGNALS (weight: {w_timing}%)
   Do the acquisition signals indicate active, near-term M&A intent?
   Scan the signals provided above before scoring this dimension.
   - 9-10: One or more HIGH-strength signals with explicit M&A/acquisition language from recent periods
           -> you MUST populate supporting_quote with the strongest signal
   - 6-8:  One or more MEDIUM-strength signals showing sector/geographic expansion intent
   - 3-5:  Only LOW-strength signals present (aspirational, circumstantial, or general)
   - 0-2:  No signals found in any source - score 0 only if signals array is empty

6. PRODUCT MIX COMPLEMENTARITY (weight: {w_product}%)
   How well does the target's product offering complement (not duplicate) the buyer's existing portfolio?
   - 9-10: Target's products fill a direct gap - pure complement with no meaningful overlap
   - 6-8:  Mostly complementary - minor product overlap, strong portfolio expansion case
   - 3-5:  Partial overlap - some synergy but also some redundancy; integration would need rationalisation
   - 0-2:  Complete overlap (target is redundant) or products are entirely unrelated to buyer's needs

WEIGHTED TOTAL FORMULA:
  weighted_total = (sector_score x {w_sector}/100) + (tech_score x {w_tech}/100) +
                   (geo_score x {w_geo}/100) + (fin_score x {w_fin}/100) +
                   (timing_score x {w_timing}/100) + (product_score x {w_product}/100)
  This yields a value on a 0-10 scale. Multiply by 10 for a 0-100 display score.

MATCH REASONING - write 2-3 sentences structured as follows:
  Sentence 1: Why is this buyer a credible candidate? (sector/product fit rationale)
  Sentence 2: What would they concretely gain from acquiring the target? (capability, geography, customer base)
  Sentence 3: What is the key risk or caveat? (financial stretch, integration complexity, regulatory, or timing)
  If you reference signals, mention the source document name.

Respond in this exact JSON format:
{{
  "dimension_scores": [
    {{
      "dimension": "sector_adjacency",
      "score": 0-10,
      "weight": {w_sector},
      "justification": "one clear sentence explaining this score with specific evidence",
      "supporting_quote": "relevant signal quote if used, else null",
      "source": "source document name if quote used, else null"
    }},
    {{
      "dimension": "technology_gap",
      "score": 0-10,
      "weight": {w_tech},
      "justification": "one clear sentence explaining this score with specific evidence",
      "supporting_quote": null,
      "source": null
    }},
    {{
      "dimension": "geographic_strategy",
      "score": 0-10,
      "weight": {w_geo},
      "justification": "one clear sentence explaining this score with specific evidence",
      "supporting_quote": null,
      "source": null
    }},
    {{
      "dimension": "financial_capacity",
      "score": 0-10,
      "weight": {w_fin},
      "justification": "one clear sentence explaining this score with specific evidence",
      "supporting_quote": null,
      "source": null
    }},
    {{
      "dimension": "timing_signals",
      "score": 0-10,
      "weight": {w_timing},
      "justification": "cite the strongest signal quote if high/medium strength; explain absence if low/zero",
      "supporting_quote": "verbatim quote from highest-strength signal, or null",
      "source": "source document of that signal, or null"
    }},
    {{
      "dimension": "product_mix",
      "score": 0-10,
      "weight": {w_product},
      "justification": "one clear sentence explaining this score with specific evidence",
      "supporting_quote": null,
      "source": null
    }}
  ],
  "weighted_total": "calculated float 0-100 using the formula above",
  "match_reasoning": "2-3 sentence structured summary covering rationale, concrete gain, and key risk/caveat"
}}"""
