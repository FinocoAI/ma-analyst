import logging
from urllib.parse import urlparse

from app.clients.anthropic_client import call_claude
from app.clients.claude_search_client import enrich_url_contents
from app.clients.scraper import fetch_rendered_text_playwright, scrape_url_detailed
from app.config import settings
from app.models.target import TargetProfile
from app.prompts.target_profiling import PROFILE_SYSTEM_PROMPT, build_profile_prompt
from app.utils.retry import with_retry
from app.utils.scrape_quality import is_usable_text, text_quality_score

logger = logging.getLogger(__name__)

_STRING_FIELDS_DEFAULT_EMPTY = frozenset(
    {"company_name", "description", "sector_l1", "sector_l2", "sector_l3", "strategic_notes"}
)


def _fallback_name_from_url(url: str) -> str:
    host = urlparse(url).netloc.split("@")[-1]
    host = host.replace("www.", "").split(":")[0]
    base = host.split(".")[0] if host else "Unknown"
    return base.replace("-", " ").strip().title() or "Unknown"


def _normalize_profile_dict(data: dict, url: str) -> dict:
    out = dict(data)
    for key in _STRING_FIELDS_DEFAULT_EMPTY:
        if out.get(key) is None:
            out[key] = ""
    if not (out.get("company_name") or "").strip():
        out["company_name"] = _fallback_name_from_url(url)
    if out.get("key_technologies") is None:
        out["key_technologies"] = []
    if out.get("geographic_footprint") is None:
        out["geographic_footprint"] = []
    return out


def _map_tier_to_quality(tier: str) -> str:
    if tier == "high":
        return "high"
    if tier == "degraded_curl":
        return "curl_boost"
    return "low"


@with_retry(max_retries=2)
async def scrape_and_profile(url: str) -> TargetProfile:
    import time as _time

    t0 = _time.monotonic()
    logger.info("[PROFILER] Step 1 start | url=%s", url)

    logger.info("[PROFILER] Scraping via httpx (+ curl_cffi fallback) | url=%s", url)
    scrape_res = await scrape_url_detailed(url)
    text = scrape_res.text
    content_quality = _map_tier_to_quality(scrape_res.tier)
    logger.info(
        "[PROFILER] Scrape result | tier=%-14s | methods=%s | chars=%d | usable=%s",
        scrape_res.tier,
        scrape_res.methods,
        len(text),
        is_usable_text(text),
    )

    if not is_usable_text(text) or scrape_res.tier == "low":
        logger.info("[PROFILER] Text quality insufficient (tier=%s) - enriching with Claude web search", scrape_res.tier)
        enriched_blob = await enrich_url_contents(url, text)
        if enriched_blob.strip():
            text = (
                "=== Direct page fetch (may be incomplete for JavaScript-heavy sites) ===\n"
                f"{text[:8000]}\n\n"
                "=== Claude web-search enrichment ===\n"
                f"{enriched_blob}"
            )
            content_quality = "claude_enriched"
            logger.info("[PROFILER] Claude enrichment applied | combined_chars=%d", len(text))
        else:
            logger.warning("[PROFILER] Claude web-search enrichment returned empty text for %s", url)
    else:
        logger.debug("[PROFILER] Web-search enrichment skipped | usable=%s | tier=%s", is_usable_text(text), scrape_res.tier)

    if settings.playwright_enabled and not is_usable_text(text):
        logger.info("[PROFILER] Still insufficient - trying Playwright render | url=%s", url)
        try:
            pw_text = await fetch_rendered_text_playwright(url)
            if is_usable_text(pw_text) or text_quality_score(pw_text) > text_quality_score(text):
                text = pw_text
                content_quality = "playwright"
                logger.info("[PROFILER] Playwright render succeeded | chars=%d", len(text))
            else:
                logger.warning("[PROFILER] Playwright render did not improve quality | chars=%d", len(pw_text))
        except Exception as exc:
            logger.warning("[PROFILER] Playwright failed | url=%s | error=%s", url, exc)
    elif not settings.playwright_enabled and not is_usable_text(text):
        logger.debug("[PROFILER] Playwright disabled - skipping JS render fallback")

    if not text.strip():
        raise ValueError(f"Failed to scrape content from {url}")

    if not is_usable_text(text) and content_quality not in ("claude_enriched", "playwright"):
        content_quality = "low"

    logger.info("[PROFILER] Sending to Claude | content_quality=%-14s | chars=%d", content_quality, len(text))
    prompt = build_profile_prompt(scraped_text=text)
    result = await call_claude(
        prompt=prompt,
        system_prompt=PROFILE_SYSTEM_PROMPT,
        max_tokens=2048,
        temperature=0.0,
        response_json=True,
        label="target_profiling",
    )

    if not isinstance(result, dict):
        raise ValueError("Profiling model returned non-object JSON")

    result["url"] = url
    result["raw_scraped_text"] = text[:5000]
    result = _normalize_profile_dict(result, url)
    result["scrape_content_quality"] = content_quality
    profile = TargetProfile(**result)

    elapsed = _time.monotonic() - t0
    logger.info(
        "[PROFILER] Done in %5.1fs | company=%-30s | %s > %s > %s | scrape_quality=%s",
        elapsed,
        profile.company_name,
        profile.sector_l1,
        profile.sector_l2,
        profile.sector_l3,
        profile.scrape_content_quality,
    )
    return profile
