import asyncio
import logging

from app.clients.anthropic_client import call_claude
from app.models.prospect import Prospect
from app.models.scoring import DimensionScore, ScoredProspect, ScoringWeights
from app.models.signal import Signal, SignalStrength
from app.models.target import TargetProfile
from app.prompts.scoring import SCORING_SYSTEM_PROMPT, build_scoring_prompt

logger = logging.getLogger(__name__)


async def score_all_prospects(
    prospects: list[Prospect],
    signals_map: dict[str, list[Signal]],
    target_profile: TargetProfile,
    weights: ScoringWeights,
) -> list[ScoredProspect]:
    """Fan out scoring across all prospects."""
    target_dict = target_profile.model_dump(exclude={"raw_scraped_text"})
    weights_dict = weights.model_dump()

    tasks = [
        _score_single(prospect, signals_map.get(prospect.id, []), target_dict, weights_dict)
        for prospect in prospects
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    scored: list[ScoredProspect] = []
    for prospect, result in zip(prospects, results):
        if isinstance(result, Exception):
            logger.error(f"Scoring failed for {prospect.company_name}: {result}")
            # Assign zero score rather than dropping the prospect
            scored.append(ScoredProspect(
                prospect=prospect,
                signals=signals_map.get(prospect.id, []),
                match_reasoning="Scoring failed — insufficient data.",
            ))
        else:
            scored.append(result)

    # Sort by score, with a small boost for HIGH/MEDIUM transcript-style signals (tie-break / recall)
    def _rank_key(sp: ScoredProspect) -> tuple[float, int, int]:
        h = sum(1 for s in sp.signals if s.strength == SignalStrength.HIGH)
        m = sum(1 for s in sp.signals if s.strength == SignalStrength.MEDIUM)
        tie = min(0.35, h * 0.08 + m * 0.03)
        return (sp.weighted_total + tie, h, m)

    scored.sort(key=_rank_key, reverse=True)
    for i, sp in enumerate(scored):
        sp.rank = i + 1

    return scored


async def _score_single(
    prospect: Prospect,
    signals: list[Signal],
    target_dict: dict,
    weights_dict: dict,
) -> ScoredProspect:
    buyer_dict = prospect.model_dump()
    signals_list = [s.model_dump() for s in signals]

    prompt = build_scoring_prompt(
        target_profile=target_dict,
        buyer_profile=buyer_dict,
        signals=signals_list,
        weights=weights_dict,
    )

    result = await call_claude(
        prompt=prompt,
        system_prompt=SCORING_SYSTEM_PROMPT,
        max_tokens=2048,
        temperature=0.0,
        response_json=True,
    )

    dimension_scores = [DimensionScore(**d) for d in result.get("dimension_scores", [])]
    weighted_total = float(result.get("weighted_total", 0.0))
    match_reasoning = result.get("match_reasoning", "")

    # Pick top signal (highest strength, most recent)
    top_signal = _pick_top_signal(signals)

    return ScoredProspect(
        prospect=prospect,
        signals=signals,
        dimension_scores=dimension_scores,
        weighted_total=weighted_total,
        top_signal=top_signal,
        match_reasoning=match_reasoning,
    )


def _pick_top_signal(signals: list[Signal]) -> Signal | None:
    if not signals:
        return None
    strength_order = {SignalStrength.HIGH: 0, SignalStrength.MEDIUM: 1, SignalStrength.LOW: 2}
    return min(signals, key=lambda s: strength_order.get(s.strength, 99))
