from __future__ import annotations

import io
import logging
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.clients.anthropic_client import call_claude
from app.clients.scraper import fetch_html_best_effort, scrape_url_detailed
from app.config import settings
from app.prompts.claude_search import (
    LISTED_CANDIDATES_SYSTEM_PROMPT,
    MA_PRESS_SYSTEM_PROMPT,
    PRIVATE_CANDIDATES_SYSTEM_PROMPT,
    PROFILE_ENRICHMENT_SYSTEM_PROMPT,
    TICKER_RESOLUTION_SYSTEM_PROMPT,
    TRANSCRIPT_DISCOVERY_SYSTEM_PROMPT,
    TRANSCRIPT_METADATA_SYSTEM_PROMPT,
    build_listed_candidates_prompt,
    build_ma_press_prompt,
    build_private_candidates_prompt,
    build_profile_enrichment_prompt,
    build_transcript_discovery_prompt,
    build_ticker_resolution_prompt,
    build_transcript_metadata_prompt,
)
from app.prompts.signal_extraction import SIGNAL_GATHER_SYSTEM_PROMPT, build_signal_gather_prompt
from app.utils.symbol_utils import normalize_symbol

logger = logging.getLogger(__name__)

_TRANSCRIPT_KEYWORDS = ("transcript", "concall", "conference call", "earnings call", "q1", "q2", "q3", "q4")
_TRANSCRIPT_LINK_HINTS = ("transcript", "concall", "conference", "earnings", "announcements", ".pdf")
_LISTING_DOMAINS = ["screener.in", "nseindia.com", "bseindia.com", "moneycontrol.com"]


@dataclass
class TranscriptDocument:
    url: str
    text: str
    source: str


def _web_search_tool(max_uses: int = 6, allowed_domains: list[str] | None = None) -> dict:
    tool = {
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": max_uses,
    }
    if allowed_domains:
        tool["allowed_domains"] = allowed_domains
    return tool


def _force_web_search_choice() -> dict:
    return {
        "type": "tool",
        "name": "web_search",
        "disable_parallel_tool_use": True,
    }


def _contains_transcript_keywords(text: str) -> bool:
    haystack = (text or "").lower()
    return any(keyword in haystack for keyword in _TRANSCRIPT_KEYWORDS)


def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clean_http_url(value: str | None) -> str:
    url = (value or "").strip().split("#", 1)[0]
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return ""
    return url


def _normalize_listed_candidate(row: dict) -> dict | None:
    company_name = (row.get("company_name") or row.get("title") or "").strip()
    if not company_name:
        return None
    symbol = normalize_symbol(row.get("symbol") or row.get("ticker"))
    exchange = (row.get("exchange") or "").strip().upper()
    if exchange not in {"NSE", "BSE"}:
        exchange = ""
    revenue = row.get("estimated_revenue_usd_m")
    if revenue is not None:
        try:
            revenue = float(revenue)
        except (TypeError, ValueError):
            revenue = None
    return {
        "company_name": company_name,
        "symbol": symbol,
        "exchange": exchange,
        "estimated_revenue_usd_m": revenue,
        "sector": (row.get("sector") or "").strip(),
        "url": (row.get("url") or row.get("website_url") or "").strip(),
        "description": (row.get("description") or row.get("snippet") or "").strip(),
        "source": "claude_search",
    }


def _normalize_private_candidate(row: dict) -> dict | None:
    title = (row.get("title") or row.get("company_name") or "").strip()
    if not title:
        return None
    return {
        "title": title,
        "url": (row.get("url") or row.get("website_url") or "").strip(),
        "snippet": (row.get("snippet") or row.get("description") or "").strip(),
    }


def _dedupe_candidates(rows: Iterable[dict], key_fields: tuple[str, ...]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        key = " | ".join(str(row.get(field, "")).strip().lower() for field in key_fields)
        if not key.strip() or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _extract_candidate_links(base_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()
        label = anchor.get_text(" ", strip=True).lower()
        if not href:
            continue
        absolute = urljoin(base_url, href)
        haystack = f"{absolute.lower()} {label}"
        if any(hint in haystack for hint in _TRANSCRIPT_LINK_HINTS):
            links.append(absolute)
    return links


async def _download_pdf_text(url: str) -> str:
    from pypdf import PdfReader

    async with httpx.AsyncClient(timeout=45, follow_redirects=True, verify=False) as client:
        response = await client.get(url)
        response.raise_for_status()
    reader = PdfReader(io.BytesIO(response.content))
    text_parts = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n".join(part for part in text_parts if part).strip()


async def _fetch_document_text(url: str) -> str:
    if url.lower().endswith(".pdf"):
        return await _download_pdf_text(url)
    result = await scrape_url_detailed(url)
    return result.text


def _sort_transcripts(items: list[dict]) -> list[dict]:
    def sort_key(item: dict) -> tuple[int, int, str]:
        return (
            _safe_int(item.get("year")) or 0,
            _safe_int(item.get("quarter")) or 0,
            str(item.get("date") or ""),
        )

    return sorted(items, key=sort_key, reverse=True)


async def enrich_url_contents(url: str, thin_text: str) -> str:
    t0 = time.monotonic()
    logger.info("[CLAUDE_SEARCH] profile_enrichment | url=%s", url)
    try:
        text = await call_claude(
            prompt=build_profile_enrichment_prompt(url, thin_text),
            system_prompt=PROFILE_ENRICHMENT_SYSTEM_PROMPT,
            model=settings.claude_search_model,
            max_tokens=1800,
            temperature=0.1,
            response_json=False,
            label="claude_search/profile_enrichment",
            tools=[_web_search_tool(max_uses=5)],
            tool_choice=_force_web_search_choice(),
        )
        elapsed = time.monotonic() - t0
        logger.info("[CLAUDE_SEARCH] profile_enrichment | done in %5.1fs | chars=%d", elapsed, len(text.strip()))
        return text.strip()
    except Exception as exc:
        elapsed = time.monotonic() - t0
        logger.warning("[CLAUDE_SEARCH] profile_enrichment | FAILED in %5.1fs | error=%s", elapsed, exc)
        return ""


async def generate_company_candidates_listed(target_profile: dict, filters: dict, budget: int) -> list[dict]:
    t0 = time.monotonic()
    logger.info("[CLAUDE_SEARCH] listed_candidates | budget=%d | target=%s", budget, target_profile.get("company_name"))
    try:
        result = await call_claude(
            prompt=build_listed_candidates_prompt(target_profile, filters, budget),
            system_prompt=LISTED_CANDIDATES_SYSTEM_PROMPT,
            model=settings.claude_search_model,
            max_tokens=4096,
            temperature=0.2,
            response_json=True,
            label="claude_search/listed_candidates",
            tools=[_web_search_tool(max_uses=3)],
            tool_choice=_force_web_search_choice(),
        )
        rows = result if isinstance(result, list) else []
        normalized = [
            candidate
            for candidate in (_normalize_listed_candidate(row) for row in rows)
            if candidate is not None
        ]
        deduped = _dedupe_candidates(normalized, ("symbol", "company_name"))
        elapsed = time.monotonic() - t0
        logger.info("[CLAUDE_SEARCH] listed_candidates | done in %5.1fs | returned=%d", elapsed, len(deduped))
        return deduped[:budget]
    except Exception as exc:
        elapsed = time.monotonic() - t0
        logger.warning("[CLAUDE_SEARCH] listed_candidates | FAILED in %5.1fs | error=%s", elapsed, exc)
        return []


async def generate_company_candidates_private(target_profile: dict, filters: dict, budget: int) -> list[dict]:
    t0 = time.monotonic()
    logger.info("[CLAUDE_SEARCH] private_candidates | budget=%d | target=%s", budget, target_profile.get("company_name"))
    try:
        result = await call_claude(
            prompt=build_private_candidates_prompt(target_profile, filters, budget),
            system_prompt=PRIVATE_CANDIDATES_SYSTEM_PROMPT,
            model=settings.claude_search_model,
            max_tokens=3072,
            temperature=0.2,
            response_json=True,
            label="claude_search/private_candidates",
            tools=[_web_search_tool(max_uses=3)],
            tool_choice=_force_web_search_choice(),
        )
        rows = result if isinstance(result, list) else []
        normalized = [
            candidate
            for candidate in (_normalize_private_candidate(row) for row in rows)
            if candidate is not None
        ]
        deduped = _dedupe_candidates(normalized, ("url", "title"))
        elapsed = time.monotonic() - t0
        logger.info("[CLAUDE_SEARCH] private_candidates | done in %5.1fs | returned=%d", elapsed, len(deduped))
        return deduped[:budget]
    except Exception as exc:
        elapsed = time.monotonic() - t0
        logger.warning("[CLAUDE_SEARCH] private_candidates | FAILED in %5.1fs | error=%s", elapsed, exc)
        return []


async def resolve_ticker(company_name: str, ticker_hint: str | None) -> str | None:
    t0 = time.monotonic()
    logger.info("[CLAUDE_SEARCH] resolve_ticker | company=%r | ticker_hint=%s", company_name, ticker_hint)
    try:
        result = await call_claude(
            prompt=build_ticker_resolution_prompt(company_name, ticker_hint),
            system_prompt=TICKER_RESOLUTION_SYSTEM_PROMPT,
            model=settings.claude_search_model,
            max_tokens=256,
            temperature=0.0,
            response_json=True,
            label="claude_search/resolve_ticker",
            tools=[_web_search_tool(max_uses=4, allowed_domains=_LISTING_DOMAINS)],
            tool_choice=_force_web_search_choice(),
        )
        ticker = normalize_symbol(result.get("ticker")) if isinstance(result, dict) else ""
        elapsed = time.monotonic() - t0
        logger.info("[CLAUDE_SEARCH] resolve_ticker | done in %5.1fs | ticker=%s", elapsed, ticker or "none")
        return ticker or None
    except Exception as exc:
        elapsed = time.monotonic() - t0
        logger.warning("[CLAUDE_SEARCH] resolve_ticker | FAILED in %5.1fs | error=%s", elapsed, exc)
        return normalize_symbol(ticker_hint) or None


async def _discover_transcript_source_links(company_name: str, ticker: str, num_quarters: int) -> list[str]:
    try:
        result = await call_claude(
            prompt=build_transcript_discovery_prompt(company_name, ticker, num_quarters),
            system_prompt=TRANSCRIPT_DISCOVERY_SYSTEM_PROMPT,
            max_tokens=1536,
            temperature=0.0,
            response_json=True,
            label=f"claude_search/transcript_discovery/{ticker}",
            tools=[_web_search_tool(max_uses=8)],
            tool_choice=_force_web_search_choice(),
        )
    except Exception as exc:
        logger.warning("[CLAUDE_SEARCH] transcript_discovery FAILED | ticker=%s | error=%s", ticker, exc)
        return []

    rows = result if isinstance(result, list) else []
    links: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        url = _clean_http_url(row.get("url"))
        if not url or url in seen:
            continue
        seen.add(url)
        links.append(url)
    return links


async def _collect_transcript_documents(company_name: str, ticker: str, num_quarters: int) -> list[TranscriptDocument]:
    discovered_links = await _discover_transcript_source_links(company_name, ticker, num_quarters)
    if not discovered_links:
        return []

    candidate_links: list[str] = []
    documents: list[TranscriptDocument] = []
    max_initial_links = max(8, min(16, num_quarters * 3))
    for base_url in discovered_links[:max_initial_links]:
        if base_url.lower().endswith(".pdf"):
            candidate_links.append(base_url)
            continue
        try:
            html, _methods = await fetch_html_best_effort(base_url, timeout=30)
        except Exception as exc:
            logger.debug("[CLAUDE_SEARCH] transcript_source_fetch failed | url=%s | error=%s", base_url, exc)
            try:
                text = await _fetch_document_text(base_url)
            except Exception as inner_exc:
                logger.debug("[CLAUDE_SEARCH] transcript_doc_fetch failed | url=%s | error=%s", base_url, inner_exc)
                continue
            if text.strip() and _contains_transcript_keywords(text) and len(text) > 1500:
                documents.append(TranscriptDocument(url=base_url, text=text[:50000], source="html"))
            continue

        page_text = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
        if _contains_transcript_keywords(page_text) and len(page_text) > 1000:
            documents.append(TranscriptDocument(url=base_url, text=page_text[:50000], source="html"))
        candidate_links.extend(_extract_candidate_links(base_url, html))

    deduped_links: list[str] = []
    seen_links: set[str] = set()
    for link in [*discovered_links, *candidate_links]:
        clean = _clean_http_url(link)
        if not clean or clean in seen_links:
            continue
        seen_links.add(clean)
        deduped_links.append(clean)

    max_document_links = max(12, min(24, num_quarters * 4))
    for link in deduped_links[:max_document_links]:
        try:
            text = await _fetch_document_text(link)
        except Exception as exc:
            logger.debug("[CLAUDE_SEARCH] transcript_doc_fetch failed | url=%s | error=%s", link, exc)
            continue
        if not text.strip():
            continue
        if link.lower().endswith(".pdf") or (_contains_transcript_keywords(text) and len(text) > 1500):
            documents.append(
                TranscriptDocument(
                    url=link,
                    text=text[:50000],
                    source="pdf" if link.lower().endswith(".pdf") else "html",
                )
            )

    deduped_docs: list[TranscriptDocument] = []
    seen_doc_urls: set[str] = set()
    for doc in documents:
        if doc.url in seen_doc_urls:
            continue
        seen_doc_urls.add(doc.url)
        deduped_docs.append(doc)
    return deduped_docs


async def fetch_earnings_transcripts(ticker: str, company_name: str, num_quarters: int) -> list[dict]:
    t0 = time.monotonic()
    logger.info(
        "[CLAUDE_SEARCH] fetch_transcripts | company=%r | ticker=%s | num_quarters=%d",
        company_name,
        ticker,
        num_quarters,
    )
    documents = await _collect_transcript_documents(company_name, ticker, num_quarters)
    if not documents:
        logger.info("[CLAUDE_SEARCH] fetch_transcripts | no source documents discovered for ticker=%s", ticker)
        return []

    transcripts: list[dict] = []
    for document in documents:
        if not _contains_transcript_keywords(document.text):
            continue
        try:
            parsed = await call_claude(
                prompt=build_transcript_metadata_prompt(company_name, ticker, document.url, document.text),
                system_prompt=TRANSCRIPT_METADATA_SYSTEM_PROMPT,
                max_tokens=512,
                temperature=0.0,
                response_json=True,
                label=f"claude_search/transcript_metadata/{ticker}",
            )
        except Exception as exc:
            logger.debug("[CLAUDE_SEARCH] transcript_metadata FAILED | url=%s | error=%s", document.url, exc)
            continue

        rows = parsed if isinstance(parsed, list) else []
        for row in rows:
            quarter = _safe_int(row.get("quarter"))
            year = _safe_int(row.get("year"))
            if quarter not in {1, 2, 3, 4} or not year or len(document.text) < 1500:
                continue
            transcripts.append(
                {
                    "ticker": ticker,
                    "quarter": quarter,
                    "year": year,
                    "content": document.text,
                    "date": (row.get("date") or "").strip(),
                    "source_url": document.url,
                }
            )

    deduped: list[dict] = []
    seen_keys: set[tuple[int, int, str]] = set()
    for item in _sort_transcripts(transcripts):
        key = (
            _safe_int(item.get("year")) or 0,
            _safe_int(item.get("quarter")) or 0,
            item.get("source_url", ""),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(item)
    final = _sort_transcripts(deduped)[:num_quarters]
    elapsed = time.monotonic() - t0
    logger.info("[CLAUDE_SEARCH] fetch_transcripts | done in %5.1fs | returned=%d", elapsed, len(final))
    return final


async def gather_and_extract_signals(
    company_name: str,
    ticker: str | None,
    target_dict: dict,
) -> list[dict] | None:
    """
    One Claude call with web_search covering all 7 source types:
    earnings transcripts, annual reports, SEBI filings, investor presentations,
    board resolutions, company website/IR, and press.

    Returns raw signal dicts ready for hydration into Signal models.
    Returns None on API failure (529, timeout) so the caller can skip caching.
    """
    t0 = time.monotonic()
    logger.info(
        "[CLAUDE_SEARCH] signal_gather | company=%r | ticker=%s",
        company_name,
        ticker or "none",
    )
    try:
        result = await call_claude(
            prompt=build_signal_gather_prompt(company_name, ticker, target_dict),
            system_prompt=SIGNAL_GATHER_SYSTEM_PROMPT,
            # web_search tool overhead: ~60-70 tokens per search call × 10 searches = ~700 tokens
            # + JSON output for signals: ~200-400 tokens per signal × up to 10 signals = ~4000 tokens
            # Total headroom needed: ~6000-8000 tokens
            max_tokens=8192,
            temperature=0.0,
            response_json=True,
            label=f"signal_gather/{company_name[:30]}",
            tools=[_web_search_tool(max_uses=10)],   # 10 searches across 7 source types
            tool_choice=_force_web_search_choice(),
        )
        rows = result if isinstance(result, list) else []
        elapsed = time.monotonic() - t0
        logger.info(
            "[CLAUDE_SEARCH] signal_gather | done in %5.1fs | signals=%d | company=%r",
            elapsed,
            len(rows),
            company_name,
        )
        return rows
    except Exception as exc:
        elapsed = time.monotonic() - t0
        logger.warning(
            "[CLAUDE_SEARCH] signal_gather | FAILED in %5.1fs | company=%r | error=%s",
            elapsed,
            company_name,
            exc,
        )
        return None  # None = failure, distinct from [] = "searched but found nothing"


async def fetch_ma_press_signals(company_name: str, ticker: str | None, target_profile: dict) -> str:
    t0 = time.monotonic()
    logger.info("[CLAUDE_SEARCH] ma_press | company=%r | ticker=%s", company_name, ticker)
    try:
        text = await call_claude(
            prompt=build_ma_press_prompt(company_name, ticker, target_profile),
            system_prompt=MA_PRESS_SYSTEM_PROMPT,
            max_tokens=1800,
            temperature=0.1,
            response_json=False,
            label="claude_search/ma_press",
            tools=[_web_search_tool(max_uses=6)],
            tool_choice=_force_web_search_choice(),
        )
        cleaned = text.strip()
        if cleaned == "NO_RESULTS":
            cleaned = ""
        elapsed = time.monotonic() - t0
        logger.info("[CLAUDE_SEARCH] ma_press | done in %5.1fs | chars=%d", elapsed, len(cleaned))
        return cleaned
    except Exception as exc:
        elapsed = time.monotonic() - t0
        logger.warning("[CLAUDE_SEARCH] ma_press | FAILED in %5.1fs | error=%s", elapsed, exc)
        return ""
