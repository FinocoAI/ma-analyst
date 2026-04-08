import asyncio
import logging
import time
import uuid

from app.config import settings
from app.models.pipeline import PipelineRunRequest, PipelineStatus
from app.models.scoring import ScoringWeights
from app.models.target import TargetProfile
from app.services.prospect_generator import generate_prospects
from app.services.scorer import score_all_prospects
from app.services.signal_extractor import extract_all_signals
from app.services.target_profiler import scrape_and_profile
from app.storage.repositories import create_pipeline_run, get_pipeline_run, update_pipeline_run

logger = logging.getLogger(__name__)

PROSPECTING_TIMEOUT_SECONDS = 240
SIGNAL_EXTRACTION_TIMEOUT_SECONDS = 300
SCORING_TIMEOUT_SECONDS = 180


async def start_pipeline(request: PipelineRunRequest) -> str:
    """Create a new pipeline run and kick off Step 1 in the background."""
    run_id = str(uuid.uuid4())
    logger.info(
        "[PIPELINE] NEW RUN | id=%s | url=%s | personas=%s | num_results=%d",
        run_id,
        request.url,
        [p.value for p in request.filters.personas],
        request.filters.num_results,
    )

    await create_pipeline_run(
        run_id=run_id,
        target_url=request.url,
        user_filters=request.filters.model_dump(),
        scoring_weights=request.weights.model_dump(),
    )

    asyncio.create_task(_run_step1(run_id, request.url))
    logger.info("[PIPELINE] %s | Step 1 dispatched as background task", run_id)
    return run_id


async def _run_step1(run_id: str, url: str) -> None:
    logger.info("[PIPELINE] %s | Step 1 START | profiling | url=%s", run_id, url)
    await update_pipeline_run(run_id, status=PipelineStatus.PROFILING.value)

    try:
        t0 = time.monotonic()
        profile = await scrape_and_profile(url)
        elapsed = time.monotonic() - t0

        await update_pipeline_run(
            run_id,
            status=PipelineStatus.PROFILE_READY.value,
            target_profile=profile.model_dump(),
            step_timings={"profiling": round(elapsed, 2)},
        )
        logger.info(
            "[PIPELINE] %s | Step 1 DONE in %5.1fs | company=%s | sector=%s > %s > %s",
            run_id,
            elapsed,
            profile.company_name,
            profile.sector_l1,
            profile.sector_l2,
            profile.sector_l3,
        )
    except Exception as exc:
        logger.error("[PIPELINE] %s | Step 1 FAILED | error=%s", run_id, exc, exc_info=True)
        await update_pipeline_run(run_id, status=PipelineStatus.FAILED.value, error_message=str(exc))


async def confirm_profile_and_continue(run_id: str, profile: TargetProfile) -> None:
    """Persist the confirmed profile and kick off Steps 2-4 in the background."""
    run_data = await get_pipeline_run(run_id)
    if not run_data:
        raise ValueError(f"Pipeline run {run_id} not found")

    from app.models.pipeline import UserFilters

    filters = UserFilters(**run_data["user_filters"])
    weights = ScoringWeights(**run_data["scoring_weights"])

    await update_pipeline_run(
        run_id,
        target_profile=profile.model_dump(),
        status=PipelineStatus.PROSPECTING.value,
    )

    logger.info(
        "[PIPELINE] %s | Profile confirmed | company=%s | dispatching Steps 2-4",
        run_id,
        profile.company_name,
    )
    asyncio.create_task(_run_steps_2_to_4(run_id, profile, filters, weights))


async def _run_steps_2_to_4(
    run_id: str,
    target_profile: TargetProfile,
    filters,
    weights: ScoringWeights,
) -> None:
    timings: dict[str, float] = {}
    pipeline_t0 = time.monotonic()

    try:
        logger.info("[PIPELINE] %s | Step 2 START | prospecting", run_id)
        await update_pipeline_run(run_id, status=PipelineStatus.PROSPECTING.value)
        t0 = time.monotonic()
        internal_max = min(
            int(filters.num_results * settings.prospect_overfetch_multiplier),
            settings.prospect_max_internal,
        )
        logger.info(
            "[PIPELINE] %s | num_results=%d | overfetch_multiplier=%.1f | internal_max=%d",
            run_id,
            filters.num_results,
            settings.prospect_overfetch_multiplier,
            internal_max,
        )
        prospects, known_listed_symbols = await asyncio.wait_for(
            generate_prospects(target_profile, filters, internal_max=internal_max),
            timeout=PROSPECTING_TIMEOUT_SECONDS,
        )
        timings["prospecting"] = round(time.monotonic() - t0, 2)
        await update_pipeline_run(run_id, prospects=[p.model_dump() for p in prospects], step_timings=timings)
        logger.info(
            "[PIPELINE] %s | Step 2 DONE in %5.1fs | prospects=%d | known_symbols=%d",
            run_id,
            timings["prospecting"],
            len(prospects),
            len(known_listed_symbols),
        )

        logger.info("[PIPELINE] %s | Step 3 START | signal extraction", run_id)
        await update_pipeline_run(run_id, status=PipelineStatus.EXTRACTING_SIGNALS.value)
        t0 = time.monotonic()
        signals_map = await asyncio.wait_for(
            extract_all_signals(
                prospects=prospects,
                target_profile=target_profile,
                custom_keywords=filters.custom_signal_keywords,
                known_listed_symbols=known_listed_symbols,
            ),
            timeout=SIGNAL_EXTRACTION_TIMEOUT_SECONDS,
        )
        timings["signal_extraction"] = round(time.monotonic() - t0, 2)
        total_signals = sum(len(v) for v in signals_map.values())
        signals_serialized = {pid: [s.model_dump() for s in sigs] for pid, sigs in signals_map.items()}
        await update_pipeline_run(run_id, signals=signals_serialized, step_timings=timings)
        logger.info(
            "[PIPELINE] %s | Step 3 DONE in %5.1fs | total_signals=%d across %d prospects",
            run_id,
            timings["signal_extraction"],
            total_signals,
            len(prospects),
        )

        logger.info("[PIPELINE] %s | Step 4 START | scoring", run_id)
        await update_pipeline_run(run_id, status=PipelineStatus.SCORING.value)
        t0 = time.monotonic()
        scored_prospects = await asyncio.wait_for(
            score_all_prospects(
                prospects=prospects,
                signals_map=signals_map,
                target_profile=target_profile,
                weights=weights,
            ),
            timeout=SCORING_TIMEOUT_SECONDS,
        )
        timings["scoring"] = round(time.monotonic() - t0, 2)

        top = scored_prospects[: filters.num_results]
        for index, scored in enumerate(top):
            scored.rank = index + 1
        prospects_final = [scored.prospect for scored in top]
        signals_trimmed = {scored.prospect.id: [s.model_dump() for s in scored.signals] for scored in top}

        await update_pipeline_run(
            run_id,
            status=PipelineStatus.COMPLETE.value,
            prospects=[p.model_dump() for p in prospects_final],
            signals=signals_trimmed,
            scored_prospects=[sp.model_dump() for sp in top],
            step_timings=timings,
        )

        total_elapsed = time.monotonic() - pipeline_t0
        logger.info(
            "[PIPELINE] %s | COMPLETE in %5.1fs | profiling=%.1fs | prospecting=%.1fs | signals=%.1fs | scoring=%.1fs",
            run_id,
            total_elapsed,
            timings.get("profiling", 0),
            timings.get("prospecting", 0),
            timings.get("signal_extraction", 0),
            timings.get("scoring", 0),
        )
        if top:
            logger.info(
                "[PIPELINE] %s | Top result: #1 %-35s | score=%.1f | signals=%d",
                run_id,
                top[0].prospect.company_name,
                top[0].weighted_total,
                len(top[0].signals),
            )

    except asyncio.TimeoutError:
        logger.error("[PIPELINE] %s | FAILED | error=step timed out", run_id, exc_info=True)
        await update_pipeline_run(
            run_id,
            status=PipelineStatus.FAILED.value,
            error_message="Pipeline step timed out. Please retry with fewer results or try again shortly.",
        )
    except Exception as exc:
        logger.error("[PIPELINE] %s | FAILED | error=%s", run_id, exc, exc_info=True)
        await update_pipeline_run(run_id, status=PipelineStatus.FAILED.value, error_message=str(exc))


async def rescore_pipeline(run_id: str, new_weights: ScoringWeights) -> None:
    """Re-run Step 4 only with new weights."""
    run_data = await get_pipeline_run(run_id)
    if not run_data:
        raise ValueError(f"Pipeline run {run_id} not found")

    from app.models.prospect import Prospect
    from app.models.signal import Signal

    target_profile = TargetProfile(**run_data["target_profile"])
    prospects = [Prospect(**p) for p in run_data.get("prospects", [])]
    raw_signals = run_data.get("signals", {})
    signals_map = {pid: [Signal(**s) for s in sigs] for pid, sigs in raw_signals.items()}

    logger.info(
        "[PIPELINE] %s | RE-SCORE requested | prospects=%d | new_weights=%s",
        run_id,
        len(prospects),
        new_weights.model_dump(),
    )
    await update_pipeline_run(run_id, status=PipelineStatus.SCORING.value, scoring_weights=new_weights.model_dump())

    asyncio.create_task(_rescore_task(run_id, prospects, signals_map, target_profile, new_weights))


async def _rescore_task(run_id, prospects, signals_map, target_profile, weights):
    t0 = time.monotonic()
    try:
        scored = await asyncio.wait_for(
            score_all_prospects(prospects, signals_map, target_profile, weights),
            timeout=SCORING_TIMEOUT_SECONDS,
        )
        elapsed = time.monotonic() - t0
        await update_pipeline_run(
            run_id,
            status=PipelineStatus.COMPLETE.value,
            scored_prospects=[sp.model_dump() for sp in scored],
            scoring_weights=weights.model_dump(),
        )
        logger.info(
            "[PIPELINE] %s | RE-SCORE DONE in %5.1fs | ranked=%d | top=%s (%.1f)",
            run_id,
            elapsed,
            len(scored),
            scored[0].prospect.company_name if scored else "N/A",
            scored[0].weighted_total if scored else 0.0,
        )
    except asyncio.TimeoutError:
        logger.error("[PIPELINE] %s | RE-SCORE FAILED | error=step timed out", run_id, exc_info=True)
        await update_pipeline_run(
            run_id,
            status=PipelineStatus.FAILED.value,
            error_message="Rescoring timed out. Please retry.",
        )
    except Exception as exc:
        logger.error("[PIPELINE] %s | RE-SCORE FAILED | error=%s", run_id, exc, exc_info=True)
        await update_pipeline_run(run_id, status=PipelineStatus.FAILED.value, error_message=str(exc))
