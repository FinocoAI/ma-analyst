import asyncio
import logging
import time
import uuid

from app.clients.anthropic_client import call_claude
from app.clients.claude_search_client import (
    generate_company_candidates_listed,
    generate_company_candidates_private,
)
from app.config import settings
from app.models.pipeline import UserFilters
from app.models.prospect import Prospect
from app.models.target import TargetProfile
from app.prompts.prospect_generation import (
    PROSPECT_SYSTEM_PROMPT,
    build_listed_prospect_prompt,
    build_private_prospect_prompt,
)

logger = logging.getLogger(__name__)


async def generate_prospects(
    target_profile: TargetProfile,
    filters: UserFilters,
    internal_max: int | None = None,
) -> tuple[list[Prospect], frozenset[str]]:
    """
    Run two parallel tracks to build the prospect list.
    Returns (prospects, known_listed_symbols) for ticker validation in signal extraction.
    """
    cap = internal_max if internal_max is not None else filters.num_results
    logger.info(
        "[PROSPECTS] Step 2 start | company=%-30s | cap=%d | personas=%s | geo=%s | revenue=[%s, %s]",
        target_profile.company_name,
        cap,
        [p.value for p in filters.personas],
        filters.geography,
        filters.revenue_min_usd_m,
        filters.revenue_max_usd_m,
    )

    persona_strs = [p.value for p in filters.personas]

    t0 = time.monotonic()
    known_symbols: frozenset[str] = frozenset()
    listed: list[Prospect] = []
    private: list[Prospect] = []

    # Run tracks sequentially to avoid concurrent web-search load on the Anthropic API.
    # Listed first (higher signal quality), private second.
    logger.info("[PROSPECTS] Running listed track")
    try:
        listed_result = await asyncio.wait_for(
            _find_listed_prospects(target_profile, filters, persona_strs, cap),
            timeout=settings.prospect_track_timeout_seconds,
        )
        if isinstance(listed_result, tuple):
            listed, known_symbols = listed_result
            logger.info("[PROSPECTS] Listed track done | listed=%d | known_symbols=%d", len(listed), len(known_symbols))
    except Exception as exc:
        logger.error("[PROSPECTS] Listed track FAILED: %s", exc)

    logger.info("[PROSPECTS] Running private track")
    try:
        private_result = await asyncio.wait_for(
            _find_private_prospects(target_profile, filters, persona_strs, cap),
            timeout=settings.prospect_track_timeout_seconds,
        )
        if isinstance(private_result, list):
            private = private_result
            logger.info("[PROSPECTS] Private track done | private=%d", len(private))
    except Exception as exc:
        logger.error("[PROSPECTS] Private track FAILED: %s", exc)

    all_prospects = _merge_and_deduplicate(listed, private)
    before_cap = len(all_prospects)
    all_prospects = all_prospects[:cap]
    elapsed = time.monotonic() - t0
    logger.info(
        "[PROSPECTS] Done in %5.1fs | listed=%d | private=%d | merged=%d | after_cap=%d",
        elapsed,
        len(listed),
        len(private if not isinstance(private, Exception) else []),
        before_cap,
        len(all_prospects),
    )
    return all_prospects, known_symbols


async def _find_listed_prospects(
    target_profile: TargetProfile,
    filters: UserFilters,
    persona_strs: list[str],
    cap: int,
) -> tuple[list[Prospect], frozenset[str]]:
    budget = max(12, min(22, cap // 2 + 10))
    company_list = await generate_company_candidates_listed(
        target_profile.model_dump(exclude={"raw_scraped_text"}),
        {
            "geography": filters.geography,
            "personas": persona_strs,
            "revenue_min_usd_m": filters.revenue_min_usd_m,
            "revenue_max_usd_m": filters.revenue_max_usd_m,
        },
        budget,
    )
    known = {
        str(item.get("symbol", "")).strip().upper()
        for item in company_list
        if str(item.get("symbol", "")).strip()
    }
    logger.info("[PROSPECTS/A] Claude search returned %d listed candidates | known_symbols=%d", len(company_list), len(known))

    if not company_list:
        logger.warning("[PROSPECTS/A] No listed companies found - returning empty")
        return [], frozenset()

    prompt = build_listed_prospect_prompt(
        target_profile=target_profile.model_dump(exclude={"raw_scraped_text"}),
        company_list=company_list,
        personas=persona_strs,
        revenue_min=filters.revenue_min_usd_m,
        revenue_max=filters.revenue_max_usd_m,
        geography=filters.geography,
    )

    result = await call_claude(
        prompt=prompt,
        system_prompt=PROSPECT_SYSTEM_PROMPT,
        max_tokens=2500,
        temperature=0.2,
        response_json=True,
        label="prospect_gen/listed",
    )

    if not isinstance(result, list):
        logger.warning("[PROSPECTS/A] Claude returned non-list - returning empty")
        return [], frozenset(known)

    prospects = [Prospect(id=str(uuid.uuid4()), **p) for p in result if _is_valid_prospect(p)]
    logger.info("[PROSPECTS/A] Claude selected %d valid listed prospects (from %d returned)", len(prospects), len(result))
    return prospects, frozenset(known)


async def _find_private_prospects(
    target_profile: TargetProfile,
    filters: UserFilters,
    persona_strs: list[str],
    cap: int,
) -> list[Prospect]:
    prompt_budget = max(8, min(14, cap // 3 + 6))
    candidates = await generate_company_candidates_private(
        target_profile.model_dump(exclude={"raw_scraped_text"}),
        {
            "geography": filters.geography,
            "personas": persona_strs,
        },
        prompt_budget,
    )
    logger.info("[PROSPECTS/B] Claude search returned %d private candidates", len(candidates))

    if not candidates:
        logger.warning("[PROSPECTS/B] No private companies found - returning empty")
        return []

    prompt = build_private_prospect_prompt(
        target_profile=target_profile.model_dump(exclude={"raw_scraped_text"}),
        candidate_results=candidates,
        personas=persona_strs,
        geography=filters.geography,
    )

    result = await call_claude(
        prompt=prompt,
        system_prompt=PROSPECT_SYSTEM_PROMPT,
        max_tokens=4096,
        temperature=0.3,
        response_json=True,
        label="prospect_gen/private",
    )

    if not isinstance(result, list):
        logger.warning("[PROSPECTS/B] Claude returned non-list - returning empty")
        return []

    prospects = [Prospect(id=str(uuid.uuid4()), **p) for p in result if _is_valid_prospect(p)]
    logger.info("[PROSPECTS/B] Claude selected %d valid private prospects (from %d returned)", len(prospects), len(result))
    return prospects


def _is_valid_prospect(p: dict) -> bool:
    return bool(p.get("company_name")) and bool(p.get("persona")) and bool(p.get("sector"))


def _merge_and_deduplicate(listed: list[Prospect], private: list[Prospect]) -> list[Prospect]:
    seen = set()
    merged = []
    for prospect in listed + private:
        key = prospect.company_name.lower().strip()
        if key not in seen:
            seen.add(key)
            merged.append(prospect)
    return merged
