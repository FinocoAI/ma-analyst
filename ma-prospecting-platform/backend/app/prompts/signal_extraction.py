SIGNAL_SYSTEM_PROMPT = """You are an M&A intelligence analyst specialising in acquisition signal detection.
You read earnings call transcripts and filings to identify companies actively seeking acquisitions.
Be precise. Only extract signals that are genuinely present in the text — never fabricate or infer beyond what is stated.
Respond ONLY with valid JSON — no preamble, no explanation."""


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
Also specifically look for mentions of: {', '.join(custom_keywords)}
"""

    if content_kind == "web_press":
        doc_label = "WEB / PRESS / IR SNIPPETS (not an earnings call — may be incomplete)"
        source_line = 'Use "source_document": "Web or press/IR (see URL in text if present)" and copy quotes verbatim from the snippets below.'
    else:
        doc_label = "EARNINGS CALL TRANSCRIPT"
        source_line = f'Use "source_document": "Q{quarter} Earnings Call Transcript" when the quote is from the transcript below.'

    return f"""Read the following text and extract acquisition signals relevant to a potential acquisition of the target-type company.

COMPANY BEING ANALYSED: {company_name}
PERIOD / LABEL: {quarter}

TARGET COMPANY CONTEXT (we are looking for signals that {company_name} might want to acquire a company like this):
- Sector: {target_profile.get('sector_l2')} → {target_profile.get('sector_l3')}
- Key technologies: {', '.join(target_profile.get('key_technologies', []))}
- Geography: {', '.join(target_profile.get('geographic_footprint', []))}
- What they do: {target_profile.get('description', '')}

{doc_label}:
---
{transcript_text}
---
{custom_section}
{source_line}

Look for these signal types:
1. acquisition_intent — explicit mentions of acquiring, buying, inorganic growth, M&A strategy
2. sector_expansion — interest in expanding into the target's sector or adjacent sectors
3. technology_gap — mentions of lacking capabilities the target provides
4. geographic_interest — interest in target's geography (Europe, Switzerland, etc.)
5. capex_signal — large capex budgets or guidance suggesting acquisition bandwidth
6. board_action — acquisition committee formation, board-level M&A approvals

For each signal found, return an entry in this JSON array:
[
  {{
    "quote": "exact verbatim quote from the transcript — copy word for word",
    "signal_type": "acquisition_intent" | "sector_expansion" | "technology_gap" | "geographic_interest" | "capex_signal" | "board_action",
    "strength": "high" | "medium" | "low",
    "source_document": "e.g. Q3 FY26 Earnings Call OR Web/IR press snippet",
    "source_quarter": "string matching the period label above, or N/A for web-only snippets",
    "reasoning": "1-2 sentences explaining why this signal is relevant to acquiring the target company"
  }}
]

Strength guide:
- high = explicit acquisition intent (e.g. "we are actively evaluating acquisitions in pollution control")
- medium = strong indirect indicator (e.g. "we plan to expand environmental capabilities through partnerships")
- low = weak/circumstantial (e.g. "we see opportunity in the environmental space")

CRITICAL RULES:
- The "quote" field MUST be copied verbatim from the source text above — do not paraphrase
- If no relevant signals exist, return an empty array []
- Do NOT fabricate signals — only extract what is genuinely in the text
- Ignore signals unrelated to the target's sector, technology, or geography"""
