from enum import Enum

from pydantic import BaseModel


class BuyerPersona(str, Enum):
    STRATEGIC = "strategic"
    PRIVATE_EQUITY = "private_equity"
    CONGLOMERATE = "conglomerate"


class Prospect(BaseModel):
    id: str
    company_name: str
    ticker: str | None = None
    is_listed: bool
    persona: BuyerPersona
    sector: str
    sector_relevance: str  # "exact_match" | "adjacent" | "tangential"
    product_mix_notes: str = ""
    estimated_revenue_inr_cr: float | None = None
    estimated_revenue_usd_m: float | None = None
    website_url: str | None = None
    source: str  # "fmp" | "exa" | "claude_search"
    country: str = "India"
