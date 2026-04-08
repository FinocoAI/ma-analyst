from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from app.models.prospect import BuyerPersona, Prospect
from app.models.scoring import ScoredProspect, ScoringWeights
from app.models.signal import Signal
from app.models.target import TargetProfile


class PipelineStatus(str, Enum):
    CREATED = "created"
    PROFILING = "profiling"
    PROFILE_READY = "profile_ready"
    PROSPECTING = "prospecting"
    EXTRACTING_SIGNALS = "extracting_signals"
    SCORING = "scoring"
    COMPLETE = "complete"
    FAILED = "failed"


class UserFilters(BaseModel):
    personas: list[BuyerPersona] = [BuyerPersona.STRATEGIC, BuyerPersona.CONGLOMERATE]
    revenue_min_usd_m: float | None = None
    revenue_max_usd_m: float | None = None
    geography: str = "India"
    custom_signal_keywords: list[str] = []
    num_results: int = 25


class PipelineRun(BaseModel):
    id: str
    created_at: datetime
    status: PipelineStatus
    target_url: str
    target_profile: TargetProfile | None = None
    user_filters: UserFilters = UserFilters()
    scoring_weights: ScoringWeights = ScoringWeights()
    prospects: list[Prospect] = []
    signals: dict[str, list[Signal]] = {}
    scored_prospects: list[ScoredProspect] = []
    error_message: str | None = None
    step_timings: dict[str, float] = {}


class PipelineRunRequest(BaseModel):
    url: str
    filters: UserFilters = UserFilters()
    weights: ScoringWeights = ScoringWeights()


class PipelineStatusResponse(BaseModel):
    run_id: str
    status: PipelineStatus
    current_step: str = ""
    progress_pct: float = 0.0
    error_message: str | None = None
    # Set when profile exists (e.g. after Step 1): high | curl_boost | exa_enriched | playwright | low
    scrape_content_quality: str | None = None
