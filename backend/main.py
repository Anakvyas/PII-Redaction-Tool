"""Entry point: `python main.py` for local dev, or `uvicorn main:app` in
production (see backend/Dockerfile)."""
from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.router import router as v1_router
from config.settings import get_settings
from core.database import SessionLocal, init_db
from core.exceptions import register_exception_handlers
from core.logging import configure_logging, get_logger
from core.middleware import RequestContextMiddleware
from services.policy_service import PolicyService

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        PolicyService(db).ensure_default_policy()
    finally:
        db.close()
    logger.info("%s started (environment=%s)", settings.APP_NAME, settings.ENVIRONMENT)
    yield
    logger.info("%s shutting down", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestContextMiddleware)

register_exception_handlers(app)
app.include_router(v1_router, prefix=settings.API_PREFIX)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "environment": settings.ENVIRONMENT}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
