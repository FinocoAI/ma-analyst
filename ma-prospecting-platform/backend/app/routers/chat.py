import logging
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.chat import ChatRequest, ChatResponse
from app.models.pipeline import PipelineStatus
from app.models.scoring import ScoredProspect
from app.models.signal import Signal
from app.models.target import TargetProfile
from app.services.chat_service import handle_chat_message, stream_chat_message
from app.storage.repositories import get_pipeline_run, save_chat_message, get_chat_history

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["chat"])


def _load_pipeline_context(run: dict):
    """Deserialise pipeline run data into typed objects."""
    if not run.get("target_profile"):
        raise HTTPException(status_code=400, detail="Pipeline has no target profile yet")
    if run["status"] != PipelineStatus.COMPLETE.value:
        raise HTTPException(status_code=400, detail="Pipeline must be complete before chatting")

    target_profile = TargetProfile(**run["target_profile"])

    scored_prospects = [ScoredProspect(**sp) for sp in (run.get("scored_prospects") or [])]

    raw_signals = run.get("signals") or {}
    signals_map = {
        pid: [Signal(**s) for s in sigs]
        for pid, sigs in raw_signals.items()
    }

    return target_profile, scored_prospects, signals_map


@router.post("/{run_id}/chat")
async def chat(run_id: str, request: ChatRequest) -> ChatResponse:
    """Send a message and get a response (non-streaming)."""
    run = await get_pipeline_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    target_profile, scored_prospects, signals_map = _load_pipeline_context(run)

    # Save user message
    await save_chat_message(str(uuid.uuid4()), run_id, "user", request.message)

    response_text = await handle_chat_message(
        run_id=run_id,
        user_message=request.message,
        target_profile=target_profile,
        scored_prospects=scored_prospects,
        all_signals=signals_map,
    )

    # Save assistant response
    await save_chat_message(str(uuid.uuid4()), run_id, "assistant", response_text)

    return ChatResponse(response=response_text)


@router.post("/{run_id}/chat/stream")
async def chat_stream(run_id: str, request: ChatRequest):
    """Send a message and get a streaming response."""
    run = await get_pipeline_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    target_profile, scored_prospects, signals_map = _load_pipeline_context(run)

    await save_chat_message(str(uuid.uuid4()), run_id, "user", request.message)

    async def generate():
        full_response = []
        async for chunk in stream_chat_message(
            run_id=run_id,
            user_message=request.message,
            target_profile=target_profile,
            scored_prospects=scored_prospects,
            all_signals=signals_map,
        ):
            full_response.append(chunk)
            yield chunk

        # Save full response after streaming completes
        await save_chat_message(str(uuid.uuid4()), run_id, "assistant", "".join(full_response))

    return StreamingResponse(generate(), media_type="text/plain")


@router.get("/{run_id}/chat/history")
async def get_history(run_id: str):
    """Get full chat history for a run."""
    run = await get_pipeline_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    history = await get_chat_history(run_id)
    return {"messages": history, "total": len(history)}
