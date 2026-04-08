import json

PROFILE_SYSTEM_PROMPT = """You are a senior M&A analyst specialising in cross-border transactions.
Your job is to analyse a company's website content and produce a structured acquisition profile.
Be factual. Only extract information that is clearly present or strongly inferable from the content.
If the source is thin, boilerplate-only, or unclear, use empty strings for unknown text fields and brief neutral strategic_notes — do not claim the text is "binary", "corrupted", or "encoded" unless it is obviously not human language.
Respond ONLY with valid JSON — no preamble, no explanation."""


def build_profile_prompt(scraped_text: str) -> str:
    return f"""Analyse the following website content and produce a structured company profile.

Website content:
---
{scraped_text}
---

Extract the following and respond in this exact JSON format:
{{
  "company_name": "string",
  "description": "2-3 sentence summary of what the company does",
  "sector_l1": "Broad industry group e.g. Industrials, Technology, Healthcare",
  "sector_l2": "Sub-sector e.g. Environmental Services, Industrial Automation",
  "sector_l3": "Specific niche e.g. Air Pollution Control, Electrostatic Precipitators",
  "key_technologies": ["list", "of", "key", "technologies", "or", "IP"],
  "estimated_employees": null or integer,
  "estimated_revenue_usd": "range string e.g. '10M-30M' or null if not inferable",
  "geographic_footprint": ["list", "of", "countries", "or", "regions"],
  "years_in_operation": null or integer,
  "india_connection": "any India presence, customers, or partnerships — null if none found",
  "strategic_notes": "What makes this company valuable to an acquirer — unique IP, market position, customer base, certifications"
}}

Rules:
- company_name, description, sector_l1, sector_l2, sector_l3, and strategic_notes MUST be strings — use "" if unknown, never JSON null
- Use null only for estimated_employees, estimated_revenue_usd, years_in_operation, or india_connection when not inferable
- Do not fabricate revenue or employee numbers — only estimate if directly stated or clearly inferable
- sector_l3 should be the most specific classification possible
- strategic_notes is the most important field — be specific about the acquirable value
- If multiple sections are provided (e.g. direct fetch vs Exa), prefer the section with clear product/company prose"""
