from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Keys
    anthropic_api_key: str

    # Claude Config
    claude_model: str = "claude-sonnet-4-6"           # analytical: profiling, signals, scoring
    claude_search_model: str = "claude-haiku-4-5-20251001"  # discovery: candidate search, ticker resolution, enrichment
    claude_max_retries: int = 3
    claude_timeout_seconds: int = 240

    # Pipeline Defaults
    default_num_results: int = 8
    default_geography: str = "India"
    transcript_quarters: int = 4
    max_concurrent_claude_calls: int = 8
    # Prospect funnel: generate more candidates than UI num_results, trim after scoring
    prospect_overfetch_multiplier: float = 2.5
    prospect_max_internal: int = 60
    prospect_track_timeout_seconds: int = 600
    # Signal extraction: limit to top-N prospects by heuristic pre-sort before running gather
    signal_extraction_limit: int = 8
    # Signal pre-filter: "strict" = regex gate before Claude; "off" = always run extraction
    signal_prefilter_mode: str = "strict"
    # Optional live web-search enrichment for press / IR mentions
    claude_web_enrichment: bool = False
    # Optional: render JS in Chromium when scrape plus web search still yield thin text
    playwright_enabled: bool = False

    # Cache
    cache_ttl_seconds: int = 86400

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # Logging
    log_level: str = "INFO"

    # Database
    database_url: str = "sqlite+aiosqlite:///./ma_prospecting.db"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
