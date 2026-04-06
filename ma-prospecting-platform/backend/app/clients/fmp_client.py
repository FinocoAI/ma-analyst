import logging
import re

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Log at most once per process: transcript endpoint often returns 402 on free FMP tiers.
_FMP_TRANSCRIPT_402_LOGGED = False


def _redact_fmp_error(msg: str) -> str:
    """Avoid leaking apikey query params into logs (httpx error strings include full URL)."""
    return re.sub(r"apikey=[^&\s'\"]+", "apikey=***", msg, flags=re.IGNORECASE)

# FMP migrated from /api/v3/ to /stable/ endpoints (v3 returns 403 on free plan)
BASE_URL = "https://financialmodelingprep.com/stable"
LEGACY_BASE_URL = "https://financialmodelingprep.com/api"


async def _fmp_get(endpoint: str, params: dict | None = None, base: str | None = None) -> dict | list:
    """Make an authenticated GET request to FMP API."""
    params = params or {}
    params["apikey"] = settings.fmp_api_key
    root = base or BASE_URL

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{root}{endpoint}", params=params)
        response.raise_for_status()
        return response.json()


async def get_earnings_transcript(ticker: str, year: int, quarter: int) -> str | None:
    """Fetch a single earnings call transcript."""
    try:
        # stable endpoint for single transcript
        data = await _fmp_get(
            f"/earning-call-transcript",
            {"symbol": ticker, "year": year, "quarter": quarter},
        )
        if data and isinstance(data, list) and len(data) > 0:
            return data[0].get("content", "")
        return None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 402:
            _log_fmp_transcript_402_once()
        else:
            logger.warning(
                "Failed to fetch transcript for %s Q%s %s: %s",
                ticker,
                quarter,
                year,
                _redact_fmp_error(str(e)),
            )
        return None
    except Exception as e:
        logger.warning(
            "Failed to fetch transcript for %s Q%s %s: %s",
            ticker,
            quarter,
            year,
            _redact_fmp_error(str(e)),
        )
        return None


def _transcript_sort_key(item: dict) -> tuple[int, int]:
    """Most recent quarter first (year desc, quarter desc)."""
    y = item.get("year")
    q = item.get("quarter")
    try:
        yi = int(y) if y is not None else 0
    except (TypeError, ValueError):
        yi = 0
    try:
        qi = int(q) if q is not None else 0
    except (TypeError, ValueError):
        qi = 0
    return (yi, qi)


def _log_fmp_transcript_402_once() -> None:
    global _FMP_TRANSCRIPT_402_LOGGED
    if _FMP_TRANSCRIPT_402_LOGGED:
        return
    _FMP_TRANSCRIPT_402_LOGGED = True
    logger.error(
        "FMP returned 402 Payment Required for earnings call transcripts — your plan does not include this "
        "endpoint, so listed-company transcript signals will be empty. Upgrade FMP (transcripts tier) or rely "
        "on Exa web enrichment if enabled. https://site.financialmodelingprep.com/developer/docs/pricing"
    )


async def get_recent_transcripts(ticker: str, num_quarters: int = 4) -> list[dict]:
    """Fetch recent earnings transcripts for a company (last N quarters)."""
    transcripts = []
    try:
        # stable endpoint: list of available transcripts for ticker
        data = await _fmp_get("/earning-call-transcript", {"symbol": ticker})
        if isinstance(data, list):
            # FMP order is not guaranteed; always take the N most recent by (year, quarter).
            sorted_items = sorted(data, key=_transcript_sort_key, reverse=True)
            for item in sorted_items[:num_quarters]:
                transcripts.append({
                    "ticker": ticker,
                    "quarter": item.get("quarter"),
                    "year": item.get("year"),
                    "content": item.get("content", ""),
                    "date": item.get("date", ""),
                })
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 402:
            _log_fmp_transcript_402_once()
        else:
            logger.warning(
                "Failed to fetch transcripts for %s: %s",
                ticker,
                _redact_fmp_error(str(e)),
            )
    except Exception as e:
        logger.warning(
            "Failed to fetch transcripts for %s: %s",
            ticker,
            _redact_fmp_error(str(e)),
        )

    return transcripts


async def resolve_listed_ticker(
    ticker: str | None,
    company_name: str,
    known_symbols: frozenset[str] | None = None,
) -> str | None:
    """
    Pick an FMP symbol for transcript fetch: prefer whitelist match, else search by company name.
    """
    from app.utils.symbol_utils import match_known_symbol, normalize_symbol

    if known_symbols:
        m = match_known_symbol(ticker, known_symbols)
        if m:
            return m

    q = (company_name or "").strip()
    if not q:
        t = normalize_symbol(ticker)
        return t if t else None

    try:
        hits = await search_companies(q, limit=12)
        if not hits:
            t = normalize_symbol(ticker)
            return t if t else None
        # Prefer exact name match, else first hit
        q_lower = q.lower()
        for h in hits:
            hn = (h.get("name") or "").lower()
            if hn == q_lower or q_lower in hn or hn in q_lower:
                sym = h.get("symbol")
                if sym:
                    return str(sym).strip().upper()
        sym = hits[0].get("symbol")
        return str(sym).strip().upper() if sym else normalize_symbol(ticker) or None
    except Exception as e:
        logger.warning(
            "resolve_listed_ticker fallback failed for %r: %s",
            company_name,
            _redact_fmp_error(str(e)),
        )
        return normalize_symbol(ticker) or None


async def search_companies(query: str, limit: int = 50) -> list[dict]:
    """Search for listed Indian companies by name using the stable FMP endpoint."""
    try:
        # /stable/search-name replaces the deprecated /v3/search (which returned 403)
        data = await _fmp_get("/search-name", {"query": query, "limit": limit, "exchange": "NSE,BSE"})
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning(
            "FMP company search failed for %r: %s",
            query,
            _redact_fmp_error(str(e)),
        )
        return []


async def get_company_profile(ticker: str) -> dict | None:
    """Get detailed company profile from FMP."""
    try:
        # stable profile endpoint
        data = await _fmp_get(f"/profile", {"symbol": ticker})
        if data and isinstance(data, list) and len(data) > 0:
            return data[0]
        return None
    except Exception as e:
        logger.warning(
            "Failed to get profile for %s: %s",
            ticker,
            _redact_fmp_error(str(e)),
        )
        return None
