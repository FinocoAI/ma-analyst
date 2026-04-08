import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health, pipeline, chat


def _setup_logging() -> None:
    """Configure root logger with a structured, readable format."""
    from app.config import settings
    log_level = settings.log_level.upper()
    numeric = getattr(logging, log_level, logging.INFO)

    # Wider format: timestamp | level | module | message
    fmt = "%(asctime)s | %(levelname)-8s | %(name)-45s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

    root = logging.getLogger()
    root.setLevel(numeric)
    # Avoid double-adding handlers on reload
    if not root.handlers:
        root.addHandler(handler)
    else:
        root.handlers.clear()
        root.addHandler(handler)

    # Quieten noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "asyncio", "multipart"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Logging configured | level=%s", log_level
    )


_setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("=" * 60)
    logger.info("M&A Prospecting Platform starting up")
    logger.info("Model: %s | Playwright: %s | Claude web enrichment: %s",
                settings.claude_model,
                settings.playwright_enabled,
                settings.claude_web_enrichment)
    logger.info("=" * 60)
    from app.storage.database import init_db
    await init_db()
    yield

    # Shutdown — close DB and let framework handle task cancellation
    logger.info("=" * 60)
    logger.info("M&A Prospecting Platform shutting down...")

    try:
        # Close database connection
        from app.storage.database import close_db
        logger.info("Closing database connection")
        await close_db()
    except Exception as e:
        logger.error("Error closing database: %s", e)

    logger.info("M&A Prospecting Platform shut down complete")
    logger.info("=" * 60)


app = FastAPI(
    title="M&A Prospecting Platform",
    description="AI-powered buyer discovery for sell-side M&A mandates",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(pipeline.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
