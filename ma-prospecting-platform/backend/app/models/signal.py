from enum import Enum

from pydantic import BaseModel


class SignalType(str, Enum):
    ACQUISITION_INTENT = "acquisition_intent"
    SECTOR_EXPANSION = "sector_expansion"
    TECHNOLOGY_GAP = "technology_gap"
    GEOGRAPHIC_INTEREST = "geographic_interest"
    CAPEX_SIGNAL = "capex_signal"
    BOARD_ACTION = "board_action"
    PRODUCT_MIX_MATCH = "product_mix_match"


class SignalStrength(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Signal(BaseModel):
    id: str
    prospect_id: str
    quote: str
    signal_type: SignalType
    strength: SignalStrength
    source_document: str
    source_quarter: str
    source_url: str | None = None
    source_context: str | None = None
    reasoning: str
