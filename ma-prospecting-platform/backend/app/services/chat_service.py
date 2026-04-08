import logging

from app.clients.anthropic_client import call_claude, call_claude_streaming
from app.models.scoring import ScoredProspect
from app.models.signal import Signal
from app.models.target import TargetProfile
from app.prompts.chat import build_chat_system_prompt
from app.storage.repositories import get_chat_history

logger = logging.getLogger(__name__)


async def handle_chat_message(
    run_id: str,
    user_message: str,
    target_profile: TargetProfile,
    scored_prospects: list[ScoredProspect],
    all_signals: dict[str, list[Signal]],
) -> str:
    """Handle a single chat message with full pipeline context."""
    target_dict = target_profile.model_dump(exclude={"raw_scraped_text"})
    prospects_list = [sp.model_dump() for sp in scored_prospects]
    signals_dict = {pid: [s.model_dump() for s in sigs] for pid, sigs in all_signals.items()}

    system_prompt = build_chat_system_prompt(
        target_profile=target_dict,
        scored_prospects=prospects_list,
        all_signals=signals_dict,
    )

    # Build conversation history for multi-turn chat
    history = await get_chat_history(run_id)
    conversation = ""
    if history:
        for msg in history[-10:]:  # Last 10 messages for context window management
            role = "User" if msg["role"] == "user" else "Assistant"
            conversation += f"{role}: {msg['content']}\n\n"

    full_prompt = conversation + f"User: {user_message}\n\nAssistant:"

    total_signals = sum(len(v) for v in all_signals.values())
    logger.info(
        "[CHAT] run=%s | mode=sync | history_turns=%d | prospects=%d | signals=%d | msg_chars=%d",
        run_id, len(history), len(scored_prospects), total_signals, len(user_message),
    )

    response = await call_claude(
        prompt=full_prompt,
        system_prompt=system_prompt,
        max_tokens=4096,
        temperature=0.4,
        response_json=False,
        label="chat/sync",
    )

    logger.info("[CHAT] run=%s | response_chars=%d", run_id, len(response))
    return response


async def stream_chat_message(
    run_id: str,
    user_message: str,
    target_profile: TargetProfile,
    scored_prospects: list[ScoredProspect],
    all_signals: dict[str, list[Signal]],
):
    """Stream a chat response for real-time display."""
    target_dict = target_profile.model_dump(exclude={"raw_scraped_text"})
    prospects_list = [sp.model_dump() for sp in scored_prospects]
    signals_dict = {pid: [s.model_dump() for s in sigs] for pid, sigs in all_signals.items()}

    system_prompt = build_chat_system_prompt(
        target_profile=target_dict,
        scored_prospects=prospects_list,
        all_signals=signals_dict,
    )

    history = await get_chat_history(run_id)
    conversation = ""
    if history:
        for msg in history[-10:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            conversation += f"{role}: {msg['content']}\n\n"

    full_prompt = conversation + f"User: {user_message}\n\nAssistant:"

    total_signals = sum(len(v) for v in all_signals.values())
    logger.info(
        "[CHAT] run=%s | mode=stream | history_turns=%d | prospects=%d | signals=%d | msg_chars=%d",
        run_id, len(history), len(scored_prospects), total_signals, len(user_message),
    )

    async for chunk in call_claude_streaming(
        prompt=full_prompt,
        system_prompt=system_prompt,
        max_tokens=4096,
        temperature=0.4,
        label="chat/stream",
    ):
        yield chunk
