"""Helpers for matching Indian listed tickers to candidate symbols."""


def normalize_symbol(raw: str | None) -> str:
    if not raw:
        return ""
    t = str(raw).strip().upper()
    if ":" in t:
        t = t.split(":")[-1]
    return t


def symbol_base(sym: str) -> str:
    """Strip common Indian exchange suffixes for comparison."""
    s = normalize_symbol(sym)
    for suf in (".NS", ".BO", ".NSE", ".BSE"):
        if s.endswith(suf):
            return s[: -len(suf)]
    return s


def match_known_symbol(ticker: str | None, known_symbols: frozenset[str]) -> str | None:
    """Return the canonical symbol from known_symbols if ticker matches, else None."""
    if not known_symbols:
        return None
    t = normalize_symbol(ticker)
    if not t:
        return None
    tb = symbol_base(t)
    for known in known_symbols:
        kn = normalize_symbol(known)
        if not kn:
            continue
        if t == kn or tb == symbol_base(kn):
            return known
    return None


def candidate_to_dict(row: dict) -> dict:
    """Normalize a candidate row for prompts and deduplication."""
    name = row.get("name") or row.get("companyName") or ""
    sym = row.get("symbol") or row.get("symbolName") or ""
    return {
        "company_name": name,
        "symbol": sym,
        "exchange": row.get("stockExchange") or row.get("exchangeShortName") or "",
        "currency": row.get("currency"),
        "source": row.get("source") or "claude_search",
    }


def collect_symbols_from_candidates(rows: list[dict]) -> set[str]:
    out: set[str] = set()
    for row in rows:
        c = candidate_to_dict(row)
        sym = c.get("symbol")
        if sym:
            out.add(str(sym).strip().upper())
    return out
