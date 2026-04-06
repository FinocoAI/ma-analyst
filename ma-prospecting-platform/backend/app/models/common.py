from pydantic import BaseModel


class Citation(BaseModel):
    source_document: str
    source_quarter: str | None = None
    source_url: str | None = None
    quote: str | None = None


class SourceReference(BaseModel):
    name: str
    url: str | None = None
    document_type: str  # "earnings_transcript" | "annual_report" | "sebi_filing" | "website"
