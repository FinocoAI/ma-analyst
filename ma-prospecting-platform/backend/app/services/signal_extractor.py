import asyncio
import logging
import time
import uuid

from app.cache.cache_manager import cache_get, cache_set
from app.cache.keys import profile_hash, signal_key
from app.clients.claude_search_client import gather_and_extract_signals
from app.config import settings
from app.models.prospect import Prospect
from app.models.signal import Signal, SignalStrength, SignalType, SourceType
from app.models.target import TargetProfile

logger = logging.getLogger(__name__)

# Heuristic weights for pre-sorting prospects before signal extraction
_RELEVANCE_SCORE = {"exact_match": 10, "adjacent": 7, "tangential": 4}
_PERSONA_SCORE = {"strategic": 3, "conglomerate": 2, "private_equity": 1}


def _heuristic_score(prospect: Prospect) -> float:
    """Fast profile-only score for pre-sorting — no Claude call."""
    return (
        _RELEVANCE_SCORE.get(prospect.sector_relevance, 0)
        + _PERSONA_SCORE.get(prospect.persona, 0)
    )


def select_top_prospects(
    prospects: list[Prospect],
    limit: int,
) -> list[Prospect]:
    """Sort by heuristic and return top-N for signal extraction."""
    sorted_prospects = sorted(prospects, key=_heuristic_score, reverse=True)
    selected = sorted_prospects[:limit]
    logger.info(
        "[SIGNALS] Pre-sort | total=%d | signal_limit=%d | selected: %s",
        len(prospects),
        limit,
        ", ".join(p.company_name for p in selected),
    )
    return selected


async def extract_all_signals(
    prospects: list[Prospect],
    target_profile: TargetProfile,
    custom_keywords: list[str] | None = None,
    known_listed_symbols: frozenset[str] | None = None,  # kept for API compat, unused
) -> dict[str, list[Signal]]:
    # Pre-sort and slice to signal_extraction_limit
    limit = settings.signal_extraction_limit
    top_prospects = select_top_prospects(prospects, limit)

    listed_count = sum(1 for p in top_prospects if p.is_listed)
    private_count = len(top_prospects) - listed_count
    logger.info(
        "[SIGNALS] Starting gather+extract | prospects=%d (listed=%d, private=%d) | concurrency=%d",
        len(top_prospects),
        listed_count,
        private_count,
        settings.max_concurrent_claude_calls,
    )

    semaphore = asyncio.Semaphore(settings.max_concurrent_claude_calls)
    target_dict = target_profile.model_dump(exclude={"raw_scraped_text"})
    ph = profile_hash(str(target_dict))

    t0 = time.monotonic()
    tasks = [
        _extract_for_prospect(prospect, target_dict, ph, semaphore)
        for prospect in top_prospects
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    signals_map: dict[str, list[Signal]] = {}
    for prospect, result in zip(top_prospects, results):
        if isinstance(result, Exception):
            logger.error("[SIGNALS] FAILED for %-35s | error=%s", prospect.company_name, result)
            signals_map[prospect.id] = []
        else:
            signals_map[prospect.id] = result

    elapsed = time.monotonic() - t0
    total = sum(len(v) for v in signals_map.values())
    high = sum(1 for sigs in signals_map.values() for s in sigs if s.strength.value == "high")
    med = sum(1 for sigs in signals_map.values() for s in sigs if s.strength.value == "medium")
    logger.info(
        "[SIGNALS] Done in %5.1fs | total=%d (high=%d, medium=%d, low=%d) across %d prospects",
        elapsed,
        total,
        high,
        med,
        total - high - med,
        len(top_prospects),
    )
    return signals_map


async def _extract_for_prospect(
    prospect: Prospect,
    target_dict: dict,
    ph: str,
    semaphore: asyncio.Semaphore,
) -> list[Signal]:
    async with semaphore:
        cache_key = signal_key(
            prospect.ticker or prospect.company_name.lower().replace(" ", "_"),
            "gather_v2",
            ph,
        )
        cached = await cache_get(cache_key)
        if cached is not None:
            signals = [Signal(**s) for s in cached]
            logger.info(
                "[SIGNALS] %-35s | cache HIT - %d signals",
                prospect.company_name,
                len(signals),
            )
            return signals

        logger.info(
            "[SIGNALS] %-35s | cache MISS | ticker=%s | running gather+extract (1 call)",
            prospect.company_name,
            prospect.ticker or "none",
        )

        raw = await gather_and_extract_signals(
            company_name=prospect.company_name,
            ticker=prospect.ticker,
            target_dict=target_dict,
        )

        signals = _hydrate_signals(raw, prospect.id)

        await cache_set(
            cache_key,
            [s.model_dump() for s in signals],
            ttl_seconds=86400 * 7,  # 7-day cache for gathered signals
        )
        logger.info(
            "[SIGNALS] %-35s | %d signals extracted | high=%d medium=%d low=%d",
            prospect.company_name,
            len(signals),
            sum(1 for s in signals if s.strength == SignalStrength.HIGH),
            sum(1 for s in signals if s.strength == SignalStrength.MEDIUM),
            sum(1 for s in signals if s.strength == SignalStrength.LOW),
        )
        return signals


def _hydrate_signals(raw: list[dict], prospect_id: str) -> list[Signal]:
    """Convert raw dicts from Claude into typed Signal models."""
    signals: list[Signal] = []
    for s in raw:
        quote = (s.get("quote") or "").strip()
        signal_type_raw = s.get("signal_type", "")
        strength_raw = s.get("strength", "")
        if not quote or not signal_type_raw or not strength_raw:
            continue

        try:
            signal_type = SignalType(signal_type_raw)
        except ValueError:
            signal_type = SignalType.ACQUISITION_INTENT

        try:
            strength = SignalStrength(strength_raw)
        except ValueError:
            strength = SignalStrength.LOW

        try:
            source_type = SourceType(s.get("source_type", "unknown"))
        except ValueError:
            source_type = SourceType.UNKNOWN

        signals.append(Signal(
            id=str(uuid.uuid4()),
            prospect_id=prospect_id,
            quote=quote,
            signal_type=signal_type,
            strength=strength,
            source_type=source_type,
            source_document=s.get("source_document", ""),
            source_quarter=s.get("source_quarter", "N/A"),
            source_url=s.get("source_url"),
            source_context=s.get("source_context"),
            reasoning=s.get("reasoning", ""),
        ))
    return signals
