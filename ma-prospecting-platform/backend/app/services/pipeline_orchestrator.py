import logging
import time
import uuid
from datetime import datetime, timezone

from app.config import settings
from app.models.pipeline import PipelineRun, PipelineStatus, PipelineRunRequest
from app.models.scoring import ScoringWeights
from app.models.target import TargetProfile
from app.services.prospect_generator import generate_prospects
from app.services.scorer import score_all_prospects
from app.services.signal_extractor import extract_all_signals
from app.services.target_profiler import scrape_and_profile
from app.storage.repositories import create_pipeline_run, get_pipeline_run, update_pipeline_run

logger = logging.getLogger(__name__)


async def start_pipeline(request: PipelineRunRequest) -> str:
    """Create a new pipeline run and kick off Step 1 (profiling)."""
    run_id = str(uuid.uuid4())

    await create_pipeline_run(
        run_id=run_id,
        target_url=request.url,
        user_filters=request.filters.model_dump(),
        scoring_weights=request.weights.model_dump(),
    )

    # Run Step 1 asynchronously (don't await — let it run in background)
    import asyncio
    asyncio.create_task(_run_step1(run_id, request.url))

    return run_id


async def _run_step1(run_id: str, url: str) -> None:
    """Step 1: Scrape and profile the target company."""
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
        logger.info(f"[{run_id}] Step 1 complete in {elapsed:.1f}s")
    except Exception as e:
        logger.error(f"[{run_id}] Step 1 failed: {e}")
        await update_pipeline_run(run_id, status=PipelineStatus.FAILED.value, error_message=str(e))


async def confirm_profile_and_continue(run_id: str, profile: TargetProfile) -> None:
    """User confirmed/edited profile — kick off Steps 2-4."""
    run_data = await get_pipeline_run(run_id)
    if not run_data:
        raise ValueError(f"Pipeline run {run_id} not found")

    from app.models.pipeline import UserFilters
    filters = UserFilters(**run_data["user_filters"])
    weights = ScoringWeights(**run_data["scoring_weights"])

    # Update profile with any user edits
    await update_pipeline_run(run_id, target_profile=profile.model_dump())

    import asyncio
    asyncio.create_task(_run_steps_2_to_4(run_id, profile, filters, weights))


async def _run_steps_2_to_4(run_id, target_profile, filters, weights) -> None:
    """Steps 2-4: Prospect generation → signal extraction → scoring."""
    timings = {}

    try:
        # Step 2: Generate prospects (internal over-fetch, then trim after scoring)
        await update_pipeline_run(run_id, status=PipelineStatus.PROSPECTING.value)
        t0 = time.monotonic()
        internal_max = min(
            int(filters.num_results * settings.prospect_overfetch_multiplier),
            settings.prospect_max_internal,
        )
        prospects, known_listed_symbols = await generate_prospects(
            target_profile, filters, internal_max=internal_max
        )
        timings["prospecting"] = round(time.monotonic() - t0, 2)
        await update_pipeline_run(run_id, prospects=[p.model_dump() for p in prospects], step_timings=timings)
        logger.info(f"[{run_id}] Step 2 complete — {len(prospects)} prospects (internal cap {internal_max})")

        # Step 3: Extract signals
        await update_pipeline_run(run_id, status=PipelineStatus.EXTRACTING_SIGNALS.value)
        t0 = time.monotonic()
        signals_map = await extract_all_signals(
            prospects=prospects,
            target_profile=target_profile,
            custom_keywords=filters.custom_signal_keywords,
            known_listed_symbols=known_listed_symbols,
        )
        timings["signal_extraction"] = round(time.monotonic() - t0, 2)
        signals_serialized = {pid: [s.model_dump() for s in sigs] for pid, sigs in signals_map.items()}
        await update_pipeline_run(run_id, signals=signals_serialized, step_timings=timings)
        logger.info(f"[{run_id}] Step 3 complete in {timings['signal_extraction']:.1f}s")

        # Step 4: Score and rank
        await update_pipeline_run(run_id, status=PipelineStatus.SCORING.value)
        t0 = time.monotonic()
        scored_prospects = await score_all_prospects(
            prospects=prospects,
            signals_map=signals_map,
            target_profile=target_profile,
            weights=weights,
        )
        timings["scoring"] = round(time.monotonic() - t0, 2)

        top = scored_prospects[: filters.num_results]
        for i, sp in enumerate(top):
            sp.rank = i + 1
        prospects_final = [sp.prospect for sp in top]
        signals_trimmed = {sp.prospect.id: [s.model_dump() for s in sp.signals] for sp in top}

        await update_pipeline_run(
            run_id,
            status=PipelineStatus.COMPLETE.value,
            prospects=[p.model_dump() for p in prospects_final],
            signals=signals_trimmed,
            scored_prospects=[sp.model_dump() for sp in top],
            step_timings=timings,
        )
        logger.info(f"[{run_id}] Pipeline complete. Top: {top[0].prospect.company_name if top else 'N/A'}")

    except Exception as e:
        logger.error(f"[{run_id}] Pipeline failed at step: {e}")
        await update_pipeline_run(run_id, status=PipelineStatus.FAILED.value, error_message=str(e))


async def rescore_pipeline(run_id: str, new_weights: ScoringWeights) -> None:
    """Re-run Step 4 only with new weights."""
    run_data = await get_pipeline_run(run_id)
    if not run_data:
        raise ValueError(f"Pipeline run {run_id} not found")

    from app.models.target import TargetProfile
    from app.models.prospect import Prospect
    from app.models.signal import Signal

    target_profile = TargetProfile(**run_data["target_profile"])
    prospects = [Prospect(**p) for p in run_data.get("prospects", [])]
    raw_signals = run_data.get("signals", {})
    signals_map = {
        pid: [Signal(**s) for s in sigs]
        for pid, sigs in raw_signals.items()
    }

    await update_pipeline_run(run_id, status=PipelineStatus.SCORING.value, scoring_weights=new_weights.model_dump())

    import asyncio
    asyncio.create_task(_rescore_task(run_id, prospects, signals_map, target_profile, new_weights))


async def _rescore_task(run_id, prospects, signals_map, target_profile, weights):
    try:
        scored = await score_all_prospects(prospects, signals_map, target_profile, weights)
        await update_pipeline_run(
            run_id,
            status=PipelineStatus.COMPLETE.value,
            scored_prospects=[sp.model_dump() for sp in scored],
            scoring_weights=weights.model_dump(),
        )
    except Exception as e:
        logger.error(f"[{run_id}] Re-scoring failed: {e}")
        await update_pipeline_run(run_id, status=PipelineStatus.FAILED.value, error_message=str(e))
