import logging
from urllib.parse import urlparse

from app.clients.anthropic_client import call_claude
from app.clients.exa_client import fetch_url_contents_for_profiling
from app.clients.scraper import fetch_rendered_text_playwright, scrape_url_detailed
from app.config import settings
from app.models.target import TargetProfile
from app.prompts.target_profiling import PROFILE_SYSTEM_PROMPT, build_profile_prompt
from app.utils.retry import with_retry
from app.utils.scrape_quality import is_usable_text, text_quality_score

logger = logging.getLogger(__name__)

# Claude sometimes returns null for fields we model as required strings — coerce before validation.
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
    """Scrape a company URL and return a structured target profile."""
    logger.info(f"Profiling target: {url}")

    scrape_res = await scrape_url_detailed(url)
    text = scrape_res.text
    content_quality = _map_tier_to_quality(scrape_res.tier)

    if settings.exa_profile_fallback and (not is_usable_text(text) or scrape_res.tier == "low"):
        exa_blob = await fetch_url_contents_for_profiling(url)
        if exa_blob.strip():
            if is_usable_text(text):
                direct_section = (
                    "=== Direct page fetch (may be incomplete for JavaScript-heavy sites) ===\n"
                    f"{text[:8000]}\n\n"
                )
            else:
                direct_section = (
                    "=== Direct page fetch omitted (unreadable or too thin; using Exa text below) ===\n\n"
                )
            text = (
                f"{direct_section}"
                "=== Exa extracted / cached text for this URL ===\n"
                f"{exa_blob}"
            )
            content_quality = "exa_enriched"
            logger.info("Profile text enriched via Exa get_contents for %s", url)

    if settings.playwright_enabled and not is_usable_text(text):
        try:
            pw_text = await fetch_rendered_text_playwright(url)
            if is_usable_text(pw_text) or text_quality_score(pw_text) > text_quality_score(text):
                text = pw_text
                content_quality = "playwright"
                logger.info("Profile text obtained via Playwright for %s", url)
        except Exception as e:
            logger.warning("Playwright profiling fallback skipped/failed for %s: %s", url, e)

    if not text.strip():
        raise ValueError(f"Failed to scrape content from {url}")

    if not is_usable_text(text) and content_quality not in ("exa_enriched", "playwright"):
        content_quality = "low"

    prompt = build_profile_prompt(scraped_text=text)
    result = await call_claude(
        prompt=prompt,
        system_prompt=PROFILE_SYSTEM_PROMPT,
        max_tokens=2048,
        temperature=0.0,
        response_json=True,
    )

    if not isinstance(result, dict):
        raise ValueError("Profiling model returned non-object JSON")

    result["url"] = url
    result["raw_scraped_text"] = text[:5000]

    result = _normalize_profile_dict(result, url)
    result["scrape_content_quality"] = content_quality
    profile = TargetProfile(**result)
    logger.info(
        "Profiled: %s | %s > %s > %s (scrape_quality=%s)",
        profile.company_name,
        profile.sector_l1,
        profile.sector_l2,
        profile.sector_l3,
        profile.scrape_content_quality,
    )
    return profile
