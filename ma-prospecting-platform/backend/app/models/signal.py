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


class SourceType(str, Enum):
    EARNINGS_TRANSCRIPT = "earnings_transcript"
    ANNUAL_REPORT = "annual_report"
    SEBI_FILING = "sebi_filing"
    INVESTOR_PRESENTATION = "investor_presentation"
    BOARD_RESOLUTION = "board_resolution"
    COMPANY_WEBSITE = "company_website"
    PRESS = "press"
    UNKNOWN = "unknown"


class Signal(BaseModel):
    id: str
    prospect_id: str
    quote: str
    signal_type: SignalType
    strength: SignalStrength
    source_type: SourceType = SourceType.UNKNOWN
    source_document: str
    source_quarter: str
    source_url: str | None = None
    source_context: str | None = None
    reasoning: str
