from pydantic import BaseModel, model_validator

from app.models.prospect import Prospect
from app.models.signal import Signal


class ScoringWeights(BaseModel):
    sector_adjacency: float = 20.0
    technology_gap: float = 20.0
    geographic_strategy: float = 15.0
    financial_capacity: float = 15.0
    timing_signals: float = 15.0
    product_mix: float = 15.0

    @model_validator(mode="after")
    def weights_sum_to_100(self):
        total = (
            self.sector_adjacency
            + self.technology_gap
            + self.geographic_strategy
            + self.financial_capacity
            + self.timing_signals
            + self.product_mix
        )
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Weights must sum to 100, got {total}")
        return self


class DimensionScore(BaseModel):
    dimension: str
    score: float  # 0-10
    weight: float  # percentage
    justification: str
    supporting_quote: str | None = None
    source: str | None = None


class ScoredProspect(BaseModel):
    prospect: Prospect
    signals: list[Signal] = []
    dimension_scores: list[DimensionScore] = []
    weighted_total: float = 0.0
    rank: int = 0
    top_signal: Signal | None = None
    match_reasoning: str = ""
