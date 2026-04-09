SIGNAL_SYSTEM_PROMPT = """You are a senior M&A intelligence analyst specialising in acquisition signal detection.
Your job is to read earnings call transcripts, regulatory filings, and press/IR snippets
and identify evidence that a company is actively pursuing acquisitions in a specific sector or geography.

Analyst rules:
- A signal only exists if it has a verbatim quote - do not infer or paraphrase
- Your reasoning must explain why THIS specific quote is relevant to THIS specific target profile
- Generic acquisition language ("we are open to M&A") is a LOW-strength signal at best
- If no relevant signals exist, return an empty array - do not pad with weak or unrelated quotes
- Respond ONLY with valid JSON - no preamble, no explanation, no markdown fences"""


def build_signal_prompt(
    company_name: str,
    transcript_text: str,
    quarter: str,
    target_profile: dict,
    custom_keywords: list[str] | None = None,
    content_kind: str = "earnings_call",
) -> str:
    custom_section = ""
    if custom_keywords:
        custom_section = f"""
Also specifically scan for mentions of: {', '.join(custom_keywords)}
"""

    if content_kind == "web_press":
        doc_label = "WEB / PRESS / IR SNIPPETS (not an earnings call - may be incomplete)"
        source_line = (
            'Use "source_document": "Web or press/IR", '
            '"source_url": "the specific URL for this snippet if present in the text", '
            'and "source_context": "the 2-3 surrounding sentences for the quote when available". '
            "Copy quotes verbatim."
        )
    else:
        doc_label = "EARNINGS CALL TRANSCRIPT"
        source_line = (
            f'Use "source_document": "{quarter} Earnings Call Transcript" when the quote is from the transcript below. '
            'Include "source_context" as the 2-3 surrounding sentences for the quote when available.'
        )

    return f"""You are an M&A analyst. Read the text below and extract acquisition signals relevant
to whether {company_name} might want to acquire a company like the target described.

COMPANY BEING ANALYSED: {company_name}
PERIOD / LABEL: {quarter}

TARGET COMPANY CONTEXT - signals must relate to this profile to be relevant:
  What the target does:   {target_profile.get('description', '')}
  Sector:                 {target_profile.get('sector_l2')} -> {target_profile.get('sector_l3')}
  Key technologies:       {', '.join(target_profile.get('key_technologies', []))}
  Geography:              {', '.join(target_profile.get('geographic_footprint', []))}
  Custom guidance:        {target_profile.get('custom_guidance', 'None provided.')}

{doc_label}:
---
{transcript_text}
---
{custom_section}
SIGNAL TYPES - definitions and evidence criteria:

1. acquisition_intent
   What qualifies: Explicit statements about acquiring companies, pursuing inorganic growth,
   evaluating M&A opportunities, building a corporate development pipeline, or hiring for BD/M&A roles.
   Example evidence: "We are actively evaluating bolt-on acquisitions in the environmental sector."

2. sector_expansion
   What qualifies: Stated plans to enter, grow within, or build new capabilities in the target's L2/L3 sector.
   The sector must be named or clearly implied - generic "growth" language does not qualify.
   Example evidence: "We see pollution control as a key growth pillar for the next 3 years."

3. technology_gap
   What qualifies: Acknowledged absence of a capability that the target provides, or stated need
   to acquire that capability externally rather than build it.
   Example evidence: "We currently do not have in-house air filtration technology - it's an area we're looking at."

4. geographic_interest
   What qualifies: Explicit interest in entering or expanding in the target's geography.
   The geography must match or overlap with the target's footprint.
   Example evidence: "We are evaluating opportunities in Europe, particularly in Switzerland and Germany."

5. capex_signal
   What qualifies: Large unallocated capex guidance, stated acquisition war chest, or balance-sheet
   commentary specifically linked to inorganic investment.
   Example evidence: "We have INR 2,000 crore earmarked for strategic acquisitions over the next 18 months."

6. board_action
   What qualifies: Board-level M&A approvals, formation of acquisition committees, disclosed acquisition
   criteria or target geographies approved by the board.
   Example evidence: "The board has approved a framework for cross-border acquisitions up to USD 100M."

STRENGTH DECISION RULE:
  high:   Quote explicitly names the sector/technology/geography AND states an active or imminent action
          (e.g. "actively evaluating", "in discussions", "have mandated advisors")
  medium: Quote shows clear directional intent - sector or geography interest is named but action is not yet confirmed
          (e.g. "we plan to", "we are looking at", "we see opportunity in")
  low:    Quote is aspirational, circumstantial, or mentions the space without clear intent
          (e.g. "we see interesting trends", "it's an area to watch")

{source_line}

REASONING REQUIREMENT:
For each signal, write 1-2 sentences that:
1. State what the quote reveals about {company_name}'s intent or strategy
2. Explain specifically how this connects to acquiring a company with the target's sector, technology, or geography

Do not write generic reasoning like "this shows acquisition interest." Connect it to the target profile above.

Return as a JSON array. Each entry must follow this schema:
[
  {{
    "quote": "exact verbatim quote from the source text - never paraphrase",
    "signal_type": "acquisition_intent" | "sector_expansion" | "technology_gap" | "geographic_interest" | "capex_signal" | "board_action",
    "strength": "high" | "medium" | "low",
    "source_document": "e.g. Q3 FY26 Earnings Call Transcript OR Web/press/IR snippet",
    "source_quarter": "string matching the period label above, or N/A for web-only snippets",
    "source_url": "URL if present in the source text, else null",
    "source_context": "2-3 surrounding sentences that help explain where the quote came from, else null",
    "reasoning": "1-2 sentences connecting this signal to the target profile"
  }}
]

Return empty array [] if no signals meet the relevance bar.
CRITICAL: "quote" must be copied verbatim - do not rephrase or summarise."""
