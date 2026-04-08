from pydantic import BaseModel, Field


class TargetProfile(BaseModel):
    company_name: str
    url: str
    description: str
    sector_l1: str
    sector_l2: str
    sector_l3: str
    key_technologies: list[str] | None = Field(default_factory=list)
    estimated_employees: int | None = None
    estimated_revenue_usd: str | None = None
    geographic_footprint: list[str] | None = Field(default_factory=list)
    years_in_operation: int | None = None
    india_connection: str | None = None
    strategic_notes: str = ""
    raw_scraped_text: str = ""
    # high | curl_boost | claude_enriched | playwright | low - how Step 1 obtained readable text
    scrape_content_quality: str = "high"


class TargetProfileRequest(BaseModel):
    url: str
