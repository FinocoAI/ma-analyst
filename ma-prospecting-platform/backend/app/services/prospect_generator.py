import asyncio
import logging
import re
import uuid

from app.clients.anthropic_client import call_claude
from app.clients.exa_client import find_similar_companies, search_companies
from app.clients.fmp_client import search_companies as fmp_search
from app.models.pipeline import UserFilters
from app.models.prospect import BuyerPersona, Prospect
from app.models.target import TargetProfile
from app.prompts.prospect_generation import (
    PROSPECT_SYSTEM_PROMPT,
    build_listed_prospect_prompt,
    build_private_prospect_prompt,
)
from app.utils.symbol_utils import collect_symbols_from_fmp_rows, fmp_row_to_candidate

logger = logging.getLogger(__name__)


def _normalize_company_key(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").lower().strip())


def _dedupe_fmp_rows(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        cand = fmp_row_to_candidate(row)
        sym = (cand.get("symbol") or "").strip().upper()
        nm = _normalize_company_key(cand.get("company_name", ""))
        key = f"sym:{sym}" if sym else f"name:{nm}"
        if not sym and not nm:
            continue
        if key not in seen:
            seen.add(key)
            out.append(row)
    return out


def _dedupe_exa_results(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for r in rows:
        url = (r.get("url") or "").strip().lower()
        title_k = _normalize_company_key(r.get("title", ""))
        key = url if url else f"t:{title_k}"
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def _merge_fmp_and_exa(fmp_rows: list[dict], exa_rows: list[dict]) -> list[dict]:
    """FMP rows first (have symbols); add Exa hits whose title is not already covered."""
    fmp_names = {_normalize_company_key(fmp_row_to_candidate(r).get("company_name", "")) for r in fmp_rows}
    combined: list[dict] = [fmp_row_to_candidate(r) for r in fmp_rows]
    for r in exa_rows:
        title = r.get("title", "")
        if _normalize_company_key(title) in fmp_names:
            continue
        combined.append(
            {
                "company_name": title,
                "symbol": "",
                "exchange": "",
                "url": r.get("url"),
                "description": r.get("snippet", ""),
                "source": "exa",
            }
        )
    return combined


async def generate_prospects(
    target_profile: TargetProfile,
    filters: UserFilters,
    internal_max: int | None = None,
) -> tuple[list[Prospect], frozenset[str]]:
    """
    Run two parallel tracks to build prospect list.
    Returns (prospects, known_listed_symbols_from_fmp) for ticker validation in signal extraction.
    """
    cap = internal_max if internal_max is not None else filters.num_results
    logger.info(f"Generating prospects for: {target_profile.company_name} (internal cap={cap})")

    persona_strs = [p.value for p in filters.personas]

    listed_task = _find_listed_prospects(target_profile, filters, persona_strs, cap)
    private_task = _find_private_prospects(target_profile, filters, persona_strs, cap)

    listed_result, private = await asyncio.gather(listed_task, private_task, return_exceptions=True)

    known_symbols: frozenset[str] = frozenset()
    listed: list[Prospect] = []

    if isinstance(listed_result, Exception):
        logger.error(f"Listed prospect track failed: {listed_result}")
    elif isinstance(listed_result, tuple):
        listed, known_symbols = listed_result
    if isinstance(private, Exception):
        logger.error(f"Private prospect track failed: {private}")
        private = []

    all_prospects = _merge_and_deduplicate(listed, private)
    all_prospects = all_prospects[:cap]
    logger.info(f"Found {len(all_prospects)} prospects ({len(listed)} listed, {len(private)} private)")
    return all_prospects, known_symbols


async def _find_listed_prospects(
    target_profile: TargetProfile,
    filters: UserFilters,
    persona_strs: list[str],
    cap: int,
) -> tuple[list[Prospect], frozenset[str]]:
    """Track A: Search for listed Indian companies; return prospects + FMP symbol whitelist."""
    geo = filters.geography
    l2, l3 = target_profile.sector_l2, target_profile.sector_l3
    techs = (target_profile.key_technologies or [])[:3]

    fmp_queries = [
        f"{l2} {l3} {geo}",
        f"{l3} listed company {geo}",
        f"{l2} NSE BSE {geo}",
    ]
    fmp_limits = max(25, min(55, cap + 15))

    fmp_tasks = [fmp_search(q, limit=fmp_limits) for q in fmp_queries]
    fmp_chunks = await asyncio.gather(*fmp_tasks, return_exceptions=True)
    fmp_raw: list[dict] = []
    for chunk in fmp_chunks:
        if isinstance(chunk, list):
            fmp_raw.extend(chunk)
        elif isinstance(chunk, Exception):
            logger.warning(f"FMP search failed in multi-query: {chunk}")

    fmp_deduped = _dedupe_fmp_rows(fmp_raw)
    known = collect_symbols_from_fmp_rows(fmp_deduped)

    exa_n = max(12, min(28, cap // 2 + 10))
    exa_queries = [
        f"Indian listed company {l2} {geo}",
        f"{l3} {geo} strategic buyer listed company NSE BSE",
        f"India inorganic growth M&A {l2} listed acquirer",
    ]
    for t in techs:
        if t and len(t) > 2:
            exa_queries.append(f"India listed company {t} {l2} manufacturer")

    exa_tasks = [search_companies(q, num_results=min(exa_n, 22)) for q in exa_queries]
    exa_chunks = await asyncio.gather(*exa_tasks, return_exceptions=True)
    exa_raw: list[dict] = []
    for chunk in exa_chunks:
        if isinstance(chunk, list):
            exa_raw.extend(chunk)
        elif isinstance(chunk, Exception):
            logger.warning(f"Exa search failed in multi-query: {chunk}")

    exa_deduped = _dedupe_exa_results(exa_raw)
    company_list = _merge_fmp_and_exa(fmp_deduped, exa_deduped)

    budget = max(55, min(95, cap * 2 + 20))
    company_list = company_list[:budget]

    if not company_list:
        return [], frozenset()

    prompt = build_listed_prospect_prompt(
        target_profile=target_profile.model_dump(exclude={"raw_scraped_text"}),
        company_list=company_list,
        personas=persona_strs,
        revenue_min=filters.revenue_min_usd_m,
        revenue_max=filters.revenue_max_usd_m,
        geography=geo,
    )

    result = await call_claude(
        prompt=prompt,
        system_prompt=PROSPECT_SYSTEM_PROMPT,
        max_tokens=4096,
        temperature=0.2,
        response_json=True,
    )

    if not isinstance(result, list):
        return [], frozenset(known)

    prospects = [Prospect(id=str(uuid.uuid4()), **p) for p in result if _is_valid_prospect(p)]
    return prospects, frozenset(known)


async def _find_private_prospects(
    target_profile: TargetProfile,
    filters: UserFilters,
    persona_strs: list[str],
    cap: int,
) -> list[Prospect]:
    """Track B: Find private Indian companies via Exa."""
    exa_n = max(12, min(26, cap // 2 + 8))
    similar_n = max(12, min(22, cap // 2 + 6))

    similar_task = find_similar_companies(target_profile.url, num_results=similar_n)
    q1 = f"private Indian company {target_profile.sector_l3} manufacturer {filters.geography}"
    q2 = f"India unlisted company {target_profile.sector_l2} {target_profile.sector_l3} acquisition"
    searched_task = asyncio.gather(
        search_companies(q1, num_results=exa_n),
        search_companies(q2, num_results=exa_n),
    )

    similar, searched_pair = await asyncio.gather(similar_task, searched_task, return_exceptions=True)
    if isinstance(similar, Exception):
        logger.warning(f"find_similar failed: {similar}")
        similar = []
    if isinstance(searched_pair, Exception):
        logger.warning(f"private Exa search failed: {searched_pair}")
        searched: list[dict] = []
    else:
        a, b = searched_pair
        searched = (a if isinstance(a, list) else []) + (b if isinstance(b, list) else [])

    combined = _dedupe_exa_results((similar if isinstance(similar, list) else []) + searched)

    prompt_budget = max(35, min(55, cap + 10))
    combined = combined[:prompt_budget]

    if not combined:
        return []

    prompt = build_private_prospect_prompt(
        target_profile=target_profile.model_dump(exclude={"raw_scraped_text"}),
        exa_results=combined,
        personas=persona_strs,
        geography=filters.geography,
    )

    result = await call_claude(
        prompt=prompt,
        system_prompt=PROSPECT_SYSTEM_PROMPT,
        max_tokens=4096,
        temperature=0.3,
        response_json=True,
    )

    if not isinstance(result, list):
        return []

    return [Prospect(id=str(uuid.uuid4()), **p) for p in result if _is_valid_prospect(p)]


def _is_valid_prospect(p: dict) -> bool:
    return bool(p.get("company_name")) and bool(p.get("persona")) and bool(p.get("sector"))


def _merge_and_deduplicate(listed: list[Prospect], private: list[Prospect]) -> list[Prospect]:
    """Merge both lists, remove duplicates by company name, preserve order."""
    seen = set()
    merged = []
    for prospect in listed + private:
        key = prospect.company_name.lower().strip()
        if key not in seen:
            seen.add(key)
            merged.append(prospect)
    return merged
