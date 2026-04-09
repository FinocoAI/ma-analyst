import asyncio
import logging
import time
import uuid

from app.cache.cache_manager import cache_get, cache_set
from app.cache.keys import profile_hash, signal_key
from app.clients.anthropic_client import call_claude
from app.clients.claude_search_client import (
    fetch_earnings_transcripts,
    fetch_ma_press_signals,
    resolve_ticker,
)
from app.config import settings
from app.models.prospect import Prospect
from app.models.signal import Signal, SignalStrength, SignalType
from app.models.target import TargetProfile
from app.prompts.signal_extraction import SIGNAL_SYSTEM_PROMPT, build_signal_prompt
from app.utils.symbol_utils import match_known_symbol
from app.utils.text_processing import chunk_text, has_acquisition_keywords

logger = logging.getLogger(__name__)


async def extract_all_signals(
    prospects: list[Prospect],
    target_profile: TargetProfile,
    custom_keywords: list[str] | None = None,
    known_listed_symbols: frozenset[str] | None = None,
) -> dict[str, list[Signal]]:
    listed_count = sum(1 for p in prospects if p.is_listed)
    private_count = len(prospects) - listed_count
    logger.info(
        "[SIGNALS] Starting extraction | prospects=%d (listed=%d, private=%d) | concurrency=%d | prefilter=%s | keywords=%d",
        len(prospects),
        listed_count,
        private_count,
        settings.max_concurrent_claude_calls,
        settings.signal_prefilter_mode,
        len(custom_keywords or []),
    )

    semaphore = asyncio.Semaphore(settings.max_concurrent_claude_calls)
    target_dict = target_profile.model_dump(exclude={"raw_scraped_text"})
    ph = profile_hash(str(target_dict))
    kw = custom_keywords or []
    known = known_listed_symbols or frozenset()

    t0 = time.monotonic()
    tasks = [_extract_for_prospect(prospect, target_dict, ph, kw, known, semaphore) for prospect in prospects]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    signals_map: dict[str, list[Signal]] = {}
    for prospect, result in zip(prospects, results):
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
        len(prospects),
    )
    return signals_map


async def _extract_for_prospect(
    prospect: Prospect,
    target_dict: dict,
    ph: str,
    custom_keywords: list[str],
    known_listed_symbols: frozenset[str],
    semaphore: asyncio.Semaphore,
) -> list[Signal]:
    async with semaphore:
        if not prospect.is_listed:
            sigs = _generate_private_signals(prospect)
            logger.info("[SIGNALS] %-35s | private company | synthetic signals=%d", prospect.company_name, len(sigs))
            return sigs

        resolved = match_known_symbol(prospect.ticker, known_listed_symbols)
        if not resolved:
            resolved = await resolve_ticker(prospect.company_name, prospect.ticker)
        ticker_for_fetch = resolved or prospect.ticker
        if not ticker_for_fetch:
            logger.info("[SIGNALS] %-35s | no resolvable ticker - skipping", prospect.company_name)
            return []

        logger.info("[SIGNALS] %-35s | listed | ticker=%s (raw=%s)", prospect.company_name, ticker_for_fetch, prospect.ticker)

        prefilter_mode = (settings.signal_prefilter_mode or "strict").lower()
        transcripts = await _get_transcripts_cached(ticker_for_fetch, prospect.company_name)
        if not transcripts:
            logger.info("[SIGNALS] %-35s | ticker=%s | no transcripts available", prospect.company_name, ticker_for_fetch)

        all_signals: list[Signal] = []
        prefilter_skipped = 0
        cache_hits = 0
        claude_calls = 0

        for transcript in transcripts:
            content = transcript.get("content", "")
            quarter = f"Q{transcript.get('quarter')} FY{str(transcript.get('year', ''))[-2:]}"
            source_url = transcript.get("source_url")

            if not has_acquisition_keywords(content, custom_keywords, mode=prefilter_mode):
                logger.debug("[SIGNALS] %-35s | %s | prefilter SKIP (mode=%s)", prospect.company_name, quarter, prefilter_mode)
                prefilter_skipped += 1
                continue

            cache_key = signal_key(ticker_for_fetch, quarter, ph)
            cached = await cache_get(cache_key)
            if cached is not None:
                cache_hits += 1
                sigs_from_cache = [_hydrate_signal_source(Signal(**s), source_url) for s in cached]
                logger.info("[SIGNALS] %-35s | %s | cache HIT - %d signals", prospect.company_name, quarter, len(sigs_from_cache))
                all_signals.extend(sigs_from_cache)
                continue

            logger.info("[SIGNALS] %-35s | %s | cache MISS - calling Claude | chars=%d", prospect.company_name, quarter, len(content))
            claude_calls += 1
            signals = await _extract_from_transcript(
                company_name=prospect.company_name,
                transcript_text=content,
                quarter=quarter,
                target_dict=target_dict,
                prospect_id=prospect.id,
                custom_keywords=custom_keywords or None,
                content_kind="earnings_call",
                source_url=source_url,
            )
            logger.info("[SIGNALS] %-35s | %s | Claude returned %d signals", prospect.company_name, quarter, len(signals))

            await cache_set(cache_key, [s.model_dump() for s in signals])
            all_signals.extend(signals)

        logger.info(
            "[SIGNALS] %-35s | transcripts=%d | prefilter_skipped=%d | cache_hits=%d | claude_calls=%d | signals=%d",
            prospect.company_name,
            len(transcripts),
            prefilter_skipped,
            cache_hits,
            claude_calls,
            len(all_signals),
        )

        if settings.claude_web_enrichment:
            logger.info("[SIGNALS] %-35s | Claude web enrichment enabled - fetching M&A press", prospect.company_name)
            web_text = await fetch_ma_press_signals(prospect.company_name, ticker_for_fetch, target_dict)
            if web_text.strip():
                wkey = signal_key(ticker_for_fetch, "web_enrichment", ph)
                cached_web = await cache_get(wkey)
                if cached_web is not None:
                    web_cached_sigs = [Signal(**s) for s in cached_web]
                    logger.info("[SIGNALS] %-35s | Claude web | cache HIT - %d signals", prospect.company_name, len(web_cached_sigs))
                    all_signals.extend(web_cached_sigs)
                elif not has_acquisition_keywords(web_text, custom_keywords, mode=prefilter_mode):
                    logger.debug("[SIGNALS] %-35s | Claude web | prefilter SKIP", prospect.company_name)
                else:
                    logger.info("[SIGNALS] %-35s | Claude web | calling Claude | chars=%d", prospect.company_name, len(web_text))
                    web_signals = await _extract_from_transcript(
                        company_name=prospect.company_name,
                        transcript_text=web_text,
                        quarter="Web/IR",
                        target_dict=target_dict,
                        prospect_id=prospect.id,
                        custom_keywords=custom_keywords or None,
                        content_kind="web_press",
                    )
                    logger.info("[SIGNALS] %-35s | Claude web | Claude returned %d signals", prospect.company_name, len(web_signals))
                    await cache_set(wkey, [s.model_dump() for s in web_signals])
                    all_signals.extend(web_signals)
            else:
                logger.info("[SIGNALS] %-35s | Claude web | no snippets returned", prospect.company_name)

        return all_signals


async def _get_transcripts_cached(ticker: str, company_name: str) -> list[dict]:
    cache_key = f"transcripts:{ticker}"
    cached = await cache_get(cache_key)
    if cached:
        logger.info("[SIGNALS] Transcript cache HIT for ticker=%s | quarters=%d", ticker, len(cached))
        return cached

    logger.info("[SIGNALS] Transcript cache MISS for ticker=%s - fetching from public sources", ticker)
    transcripts = await fetch_earnings_transcripts(ticker, company_name, settings.transcript_quarters)
    if transcripts:
        await cache_set(cache_key, transcripts, ttl_seconds=86400 * 30)
    else:
        logger.info("[SIGNALS] %s | No transcripts available from any source - skipping signal extraction", company_name)
    return transcripts


async def _extract_from_transcript(
    company_name: str,
    transcript_text: str,
    quarter: str,
    target_dict: dict,
    prospect_id: str,
    custom_keywords: list[str] | None,
    content_kind: str = "earnings_call",
    source_url: str | None = None,
) -> list[Signal]:
    chunks = chunk_text(transcript_text, max_chars=40000)
    all_raw_signals = []

    for chunk in chunks:
        prompt = build_signal_prompt(
            company_name=company_name,
            transcript_text=chunk,
            quarter=quarter,
            target_profile=target_dict,
            custom_keywords=custom_keywords,
            content_kind=content_kind,
        )
        try:
            result = await call_claude(
                prompt=prompt,
                system_prompt=SIGNAL_SYSTEM_PROMPT,
                max_tokens=2048,
                temperature=0.0,
                response_json=True,
                label=f"signal_extraction/{company_name[:20]}/{quarter}",
            )
            if isinstance(result, list):
                all_raw_signals.extend(result)
        except Exception as exc:
            logger.warning("[SIGNALS] Claude call FAILED for %s %s: %s", company_name, quarter, exc)

    return [
        Signal(
            id=str(uuid.uuid4()),
            prospect_id=prospect_id,
            quote=s.get("quote", ""),
            signal_type=SignalType(s.get("signal_type", "acquisition_intent")),
            strength=SignalStrength(s.get("strength", "low")),
            source_document=s.get("source_document", f"{quarter} Earnings Call"),
            source_quarter=s.get("source_quarter", quarter),
            source_url=s.get("source_url") or source_url,
            source_context=s.get("source_context"),
            reasoning=s.get("reasoning", ""),
        )
        for s in all_raw_signals
        if s.get("quote") and s.get("signal_type") and s.get("strength")
    ]


def _generate_private_signals(prospect: Prospect) -> list[Signal]:
    if not prospect.product_mix_notes:
        return []
    return [
        Signal(
            id=str(uuid.uuid4()),
            prospect_id=prospect.id,
            quote=prospect.product_mix_notes,
            signal_type=SignalType.PRODUCT_MIX_MATCH,
            strength=SignalStrength.MEDIUM if prospect.sector_relevance == "exact_match" else SignalStrength.LOW,
            source_document="Company Profile",
            source_quarter="N/A",
            source_url=prospect.website_url,
            reasoning=f"Private company with {prospect.sector_relevance} sector relevance and complementary product mix.",
        )
    ]


def _hydrate_signal_source(signal: Signal, source_url: str | None) -> Signal:
    if signal.source_url or not source_url:
        return signal
    return signal.model_copy(update={"source_url": source_url})
