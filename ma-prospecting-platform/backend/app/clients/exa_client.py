import asyncio
import logging

from exa_py import Exa

from app.config import settings

logger = logging.getLogger(__name__)

_exa_client: Exa | None = None


def _get_exa() -> Exa:
    global _exa_client
    if _exa_client is None:
        _exa_client = Exa(api_key=settings.exa_api_key)
    return _exa_client


def _get_contents_sync(url: str, max_characters: int) -> str:
    """Blocking Exa /contents call — run via asyncio.to_thread."""
    exa = _get_exa()
    resp = exa.get_contents(url, text={"max_characters": max_characters})
    if not getattr(resp, "results", None):
        return ""
    parts: list[str] = []
    for r in resp.results:
        title = getattr(r, "title", None) or ""
        body = getattr(r, "text", None) or ""
        if not body.strip():
            continue
        u = getattr(r, "url", None) or url
        parts.append(f"URL: {u}\nTitle: {title}\n{body}")
    return "\n\n---\n\n".join(parts)


async def fetch_url_contents_for_profiling(url: str, max_characters: int | None = None) -> str:
    """
    Pull cached / extracted text for a URL via Exa (helps when direct scrape is an empty SPA shell).
    """
    cap = max_characters or settings.exa_profile_max_characters
    try:
        return await asyncio.to_thread(_get_contents_sync, url, cap)
    except Exception as e:
        logger.warning("Exa get_contents failed for profiling %s: %s", url, e)
        return ""


async def search_companies(query: str, num_results: int = 20) -> list[dict]:
    """Search for companies using Exa semantic search."""
    try:
        exa = _get_exa()
        results = exa.search(
            query,
            num_results=num_results,
            type="auto",          # intelligent query optimisation (replaces deprecated use_autoprompt)
            category="company",   # restrict results to company pages
            contents={"text": True},  # populate snippet text in results
        )
        return [
            {
                "title": r.title,
                "url": r.url,
                "snippet": getattr(r, "text", ""),
            }
            for r in results.results
        ]
    except Exception as e:
        logger.warning(f"Exa search failed for '{query}': {e}")
        return []


async def search_ma_press_snippets(
    company_name: str,
    ticker: str | None,
    num_results: int = 5,
) -> str:
    """
    Pull short web snippets (press, IR, news) for acquisition/M&A mentions — supplements transcripts.
    """
    parts = [company_name.strip()]
    if ticker:
        parts.append(ticker.strip())
    tail = "acquisition OR M&A OR inorganic growth OR investor relations India listed"
    query = " ".join(parts) + " " + tail
    try:
        rows = await search_companies(query, num_results=num_results)
    except Exception as e:
        logger.warning(f"Exa M&A snippet search failed for {company_name!r}: {e}")
        return ""
    blocks: list[str] = []
    for r in rows:
        snippet = (r.get("snippet") or "")[:3500]
        if not snippet.strip():
            continue
        blocks.append(f"---\nURL: {r.get('url', '')}\nTitle: {r.get('title', '')}\n{snippet}")
    return "\n".join(blocks)


async def find_similar_companies(url: str, num_results: int = 15) -> list[dict]:
    """Find companies similar to a given company URL."""
    try:
        exa = _get_exa()
        results = exa.find_similar(
            url,
            num_results=num_results,
        )
        return [
            {
                "title": r.title,
                "url": r.url,
                "snippet": getattr(r, "text", ""),
            }
            for r in results.results
        ]
    except Exception as e:
        logger.warning(f"Exa find_similar failed for '{url}': {e}")
        return []
