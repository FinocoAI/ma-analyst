import re


def chunk_text(text: str, max_chars: int = 40000, overlap: int = 500) -> list[str]:
    """Split text into chunks with overlap for context continuity."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        if end < len(text):
            # Try to break at a paragraph or sentence boundary
            break_point = text.rfind("\n\n", start + max_chars // 2, end)
            if break_point == -1:
                break_point = text.rfind(". ", start + max_chars // 2, end)
            if break_point != -1:
                end = break_point + 1
        chunks.append(text[start:end])
        start = end - overlap

    return chunks


_ACQUISITION_REGEX_KEYWORDS = [
    r"\bacquisition",
    r"\bacquir",
    r"\binorganic\s+growth",
    r"\bm&a\b",
    r"\bmerger",
    r"\btakeover",
    r"\bstrategic\s+investment",
    r"\bbuy(?:ing|out)",
    r"\bcapex",
    r"\bcapital\s+expenditure",
    r"\bexpansion\s+strateg",
    r"\bnew\s+geograph",
    r"\btechnology\s+gap",
    r"\bpollution\s+control",
    r"\benvironmental\s+service",
    r"\bstrategic\s+alternative",
    r"\bstrategic\s+alliance",
    r"\bevaluating\s+opportunit",
    r"\bcapital\s+allocation",
    r"\bconsolidat",
    r"\bbolt-on",
    r"\bbolt\s+on",
    r"\btuck-in",
    r"\btuck\s+in",
    r"\brollup",
    r"\broll-up",
    r"\broll\s+up",
    r"\bstake\s+(?:purchase|acquisition|buy)",
    r"\bminority\s+stake",
    r"\bcontrolling\s+stake",
    r"\bportfolio\s+accret",
    r"\bbuild[-\s]?out",
    r"\bplatform\s+acquisition",
    r"\badd-on\s+acquisition",
    r"\bdivestiture",
    r"\bnon-core\s+asset",
    r"\bportfolio\s+company",
    r"\bsynerg",
    r"\bfund\s+deployment",
    r"\bjoint\s+venture",
    r"\bopportunities?\s+in\b",
    r"\bgrowth\s+through\s+acquisition",
    r"\binvest(?:ment)?\s+opportunities",
]


def has_acquisition_keywords(
    text: str,
    custom_keywords: list[str] | None = None,
    mode: str = "strict",
) -> bool:
    """
    Quick keyword scan to pre-filter transcripts before sending to Claude.
    mode 'off' skips the gate (full recall). custom_keywords are substring-matched (case-insensitive).
    """
    if mode == "off":
        return True
    text_lower = text.lower()
    if custom_keywords:
        for kw in custom_keywords:
            k = (kw or "").strip().lower()
            if k and k in text_lower:
                return True
    return any(re.search(kw, text_lower) for kw in _ACQUISITION_REGEX_KEYWORDS)


def clean_json_text(text: str) -> str:
    """Clean text for safe JSON embedding."""
    text = text.replace("\\", "\\\\")
    text = text.replace('"', '\\"')
    text = text.replace("\n", "\\n")
    text = text.replace("\r", "")
    text = text.replace("\t", " ")
    return text
