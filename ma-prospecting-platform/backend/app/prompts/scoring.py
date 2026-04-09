import json

SCORING_SYSTEM_PROMPT = """You are an M&A matching engine. You score potential acquirers against a target company.
Be analytical and precise. Back every score with specific evidence from the signals provided.
ALWAYS cite specific sources (e.g., "Q3 FY25 Earnings Call") in your justifications and summary when using signals.
Respond ONLY with valid JSON — no preamble, no explanation."""


def build_scoring_prompt(
    target_profile: dict,
    buyer_profile: dict,
    signals: list[dict],
    weights: dict,
) -> str:
    return f"""Score the following potential buyer against the target company across 6 dimensions.

TARGET COMPANY:
{json.dumps(target_profile, indent=2)}

CUSTOM USER GUIDANCE (Adjust scores/reasoning to adhere to these preference):
{target_profile.get('custom_guidance') or 'None provided.'}

POTENTIAL BUYER:
{json.dumps(buyer_profile, indent=2)}

ACQUISITION SIGNALS FOUND FOR THIS BUYER:
{json.dumps(signals, indent=2) if signals else "No signals found from transcripts."}

SCORING WEIGHTS (must be reflected in weighted_total calculation):
- Sector Adjacency: {weights.get('sector_adjacency', 20)}%
- Technology Gap: {weights.get('technology_gap', 20)}%
- Geographic Strategy: {weights.get('geographic_strategy', 15)}%
- Financial Capacity: {weights.get('financial_capacity', 15)}%
- Timing Signals: {weights.get('timing_signals', 15)}%
- Product Mix Complementarity: {weights.get('product_mix', 15)}%

Respond in this exact JSON format:
{{
  "dimension_scores": [
    {{
      "dimension": "sector_adjacency",
      "score": 0-10,
      "weight": {weights.get('sector_adjacency', 20)},
      "justification": "one clear sentence explaining this score",
      "supporting_quote": "relevant signal quote if applicable, else null",
      "source": "source document name if quote used, else null"
    }},
    {{
      "dimension": "technology_gap",
      "score": 0-10,
      "weight": {weights.get('technology_gap', 20)},
      "justification": "one clear sentence explaining this score",
      "supporting_quote": null,
      "source": null
    }},
    {{
      "dimension": "geographic_strategy",
      "score": 0-10,
      "weight": {weights.get('geographic_strategy', 15)},
      "justification": "one clear sentence explaining this score",
      "supporting_quote": null,
      "source": null
    }},
    {{
      "dimension": "financial_capacity",
      "score": 0-10,
      "weight": {weights.get('financial_capacity', 15)},
      "justification": "one clear sentence explaining this score",
      "supporting_quote": null,
      "source": null
    }},
    {{
      "dimension": "timing_signals",
      "score": 0-10,
      "weight": {weights.get('timing_signals', 15)},
      "justification": "one clear sentence — cite signal quotes for timing when strength is high; 0 only if no acquisition-relevant signals",
      "supporting_quote": null,
      "source": null
    }},
    {{
      "dimension": "product_mix",
      "score": 0-10,
      "weight": {weights.get('product_mix', 15)},
      "justification": "one clear sentence explaining this score",
      "supporting_quote": null,
      "source": null
    }}
  ],
  "weighted_total": calculated float 0-100 (sum of score * weight/100 for each dimension, scaled to 100),
  "match_reasoning": "2-3 sentence summary of why this company is or isn't a strong acquirer. CITING sources from earnings calls or web search when signals are found."
}}

Scoring guidance per dimension:
- sector_adjacency: 10 = exact L3 match, 7 = L2 adjacent, 4 = L1 only, 0 = unrelated
- technology_gap: 10 = buyer explicitly lacks the target's technology, 5 = partial gap, 0 = buyer already has it
- geographic_strategy: 10 = buyer has signalled European/Swiss interest, 5 = open to cross-border, 0 = India-only focus
- financial_capacity: 10 = revenue >5x target + prior cross-border deals, 5 = revenue >2x + healthy balance sheet
- timing_signals: When signals include explicit acquisition/M&A language (especially HIGH strength with a verbatim quote), score timing_signals generously — this dimension should reflect real disclosed intent. 10 = clear HIGH-strength acquisition intent in recent periods, 7 = MEDIUM, 3 = LOW, 0 = no relevant signals
- product_mix: 10 = products directly complement (no overlap), 5 = partial overlap, 0 = complete overlap or no fit"""
