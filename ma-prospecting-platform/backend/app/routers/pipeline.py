import json
import logging

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.models.pipeline import PipelineRunRequest, PipelineStatusResponse, PipelineStatus
from app.models.scoring import ScoringWeights
from app.models.target import TargetProfile
from app.services.pipeline_orchestrator import (
    start_pipeline,
    confirm_profile_and_continue,
    rescore_pipeline,
)
from app.storage.repositories import get_pipeline_run

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run")
async def create_pipeline_run(request: PipelineRunRequest):
    """Create a new pipeline run and start profiling the target company."""
    run_id = await start_pipeline(request)
    return {"run_id": run_id, "status": "profiling"}


@router.get("/{run_id}")
async def get_pipeline(run_id: str):
    """Get full pipeline state."""
    run = await get_pipeline_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return run


@router.get("/{run_id}/status")
async def get_pipeline_status(run_id: str) -> PipelineStatusResponse:
    """Lightweight status check."""
    run = await get_pipeline_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    status = PipelineStatus(run["status"])
    progress_map = {
        PipelineStatus.CREATED: 0,
        PipelineStatus.PROFILING: 10,
        PipelineStatus.PROFILE_READY: 20,
        PipelineStatus.PROSPECTING: 35,
        PipelineStatus.EXTRACTING_SIGNALS: 60,
        PipelineStatus.SCORING: 85,
        PipelineStatus.COMPLETE: 100,
        PipelineStatus.FAILED: 0,
    }
    step_label_map = {
        PipelineStatus.CREATED: "Initialising...",
        PipelineStatus.PROFILING: "Analysing target company...",
        PipelineStatus.PROFILE_READY: "Waiting for profile confirmation...",
        PipelineStatus.PROSPECTING: "Finding potential buyers...",
        PipelineStatus.EXTRACTING_SIGNALS: "Extracting acquisition signals from transcripts...",
        PipelineStatus.SCORING: "Scoring and ranking buyers...",
        PipelineStatus.COMPLETE: "Complete",
        PipelineStatus.FAILED: "Failed",
    }

    profile = run.get("target_profile") or {}
    scrape_q = None
    if isinstance(profile, dict):
        scrape_q = profile.get("scrape_content_quality")

    return PipelineStatusResponse(
        run_id=run_id,
        status=status,
        current_step=step_label_map.get(status, ""),
        progress_pct=progress_map.get(status, 0),
        error_message=run.get("error_message"),
        scrape_content_quality=scrape_q,
    )


@router.put("/{run_id}/profile")
async def confirm_profile(run_id: str, profile: TargetProfile):
    """User confirms or edits the target profile — triggers Steps 2-4."""
    run = await get_pipeline_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    if run["status"] not in (PipelineStatus.PROFILE_READY.value, PipelineStatus.FAILED.value):
        raise HTTPException(status_code=400, detail=f"Cannot confirm profile in status: {run['status']}")

    await confirm_profile_and_continue(run_id, profile)
    return {"run_id": run_id, "status": "prospecting"}


@router.post("/{run_id}/rescore")
async def rescore(run_id: str, weights: ScoringWeights):
    """Re-run Step 4 with new scoring weights."""
    run = await get_pipeline_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    if run["status"] != PipelineStatus.COMPLETE.value:
        raise HTTPException(status_code=400, detail="Pipeline must be complete before rescoring")

    await rescore_pipeline(run_id, weights)
    return {"run_id": run_id, "status": "scoring"}


@router.get("/{run_id}/prospects")
async def get_prospects(run_id: str):
    """Get scored and ranked prospect list."""
    run = await get_pipeline_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return {"prospects": run.get("scored_prospects", []), "total": len(run.get("scored_prospects", []))}


@router.get("/{run_id}/signals")
async def get_signals(run_id: str, strength: str | None = None, signal_type: str | None = None):
    """Get all signals, optionally filtered."""
    run = await get_pipeline_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    all_signals = []
    for prospect_signals in (run.get("signals") or {}).values():
        all_signals.extend(prospect_signals)

    if strength:
        all_signals = [s for s in all_signals if s.get("strength") == strength]
    if signal_type:
        all_signals = [s for s in all_signals if s.get("signal_type") == signal_type]

    return {"signals": all_signals, "total": len(all_signals)}


@router.get("/{run_id}/events")
async def pipeline_events(run_id: str):
    """SSE stream for live pipeline progress."""
    async def event_generator():
        import asyncio
        last_status = None
        for _ in range(300):  # poll for up to 10 minutes
            run = await get_pipeline_run(run_id)
            if not run:
                yield {"event": "error", "data": json.dumps({"message": "Run not found"})}
                break

            status = run["status"]
            if status != last_status:
                last_status = status
                yield {
                    "event": "status",
                    "data": json.dumps({
                        "status": status,
                        "prospects_found": len(run.get("prospects", [])),
                        "signals_found": sum(len(v) for v in (run.get("signals") or {}).values()),
                    }),
                }

            if status in (PipelineStatus.COMPLETE.value, PipelineStatus.FAILED.value):
                yield {"event": "done", "data": json.dumps({"status": status})}
                break

            await asyncio.sleep(2)

    return EventSourceResponse(event_generator())
