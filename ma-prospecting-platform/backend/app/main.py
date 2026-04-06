from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health, pipeline, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from app.storage.database import init_db
    await init_db()
    yield
    # Shutdown


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
