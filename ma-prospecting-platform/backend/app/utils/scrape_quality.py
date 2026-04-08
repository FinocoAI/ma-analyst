"""Heuristics for whether HTML-to-text output is usable for LLM profiling (vs SPA shells / noise)."""

import re

# SPA shells often yield very little natural language after stripping scripts/nav.
MIN_STRIP_LEN = 350
MIN_ALPHA_TOKENS = 38
PRINTABLE_RATIO_FLOOR = 0.82


def alpha_token_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z]{3,}", text or ""))


def printable_ratio(text: str, sample_cap: int = 12000) -> float:
    if not text:
        return 0.0
    sample = text[:sample_cap]
    if not sample:
        return 0.0
    good = sum(1 for c in sample if c.isprintable() or c in "\n\t\r")
    return good / len(sample)


def is_usable_text(text: str) -> bool:
    """True if the string looks like readable prose, not binary/minified-JS garbage."""
    t = (text or "").strip()
    if len(t) < MIN_STRIP_LEN:
        return False
    if alpha_token_count(t) < MIN_ALPHA_TOKENS:
        return False
    if printable_ratio(t) < PRINTABLE_RATIO_FLOOR:
        return False
    return True


def text_quality_score(text: str) -> int:
    """Higher = more likely useful (for picking best of two scrapes)."""
    if not text or not text.strip():
        return 0
    words = alpha_token_count(text)
    return min(len(text), 60000) // 20 + words * 3
