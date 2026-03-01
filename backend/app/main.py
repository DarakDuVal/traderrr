"""
app/main.py — FastAPI application factory
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config.settings import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks."""
    settings = get_settings()

    # ── Startup ───────────────────────────────────────────────────────────
    # 1. Check database connection
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as exc:
        logger.error("Database connection failed: %s", exc)
    finally:
        await engine.dispose()

    # 2. Ping Celery (best-effort)
    try:
        from app.workers.celery_app import celery_app as _celery

        inspect = _celery.control.inspect()
        ping = inspect.ping()
        if ping:
            logger.info("Celery worker(s) responding: %s", list(ping.keys()))
        else:
            logger.warning("No Celery workers responded to ping")
    except Exception as exc:
        logger.warning("Celery ping skipped: %s", exc)

    yield  # ← application is running

    # ── Shutdown ──────────────────────────────────────────────────────────
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    """Application factory — builds and returns a configured FastAPI instance."""
    settings = get_settings()

    app = FastAPI(
        title="Traderrr Trading System API",
        version="1.0.0",
        description=(
            "Professional algorithmic trading system with automated signal "
            "generation, portfolio optimization, and risk management."
        ),
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────
    from app.api.routes.auth import router as auth_router
    from app.api.routes.signals import router as signals_router
    from app.api.routes.portfolio import router as portfolio_router
    from app.api.routes.risk import router as risk_router
    from app.api.routes.admin import router as admin_router
    from app.ws.router import router as ws_router

    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(signals_router, prefix="/api/v1/signals", tags=["signals"])
    app.include_router(portfolio_router, prefix="/api/v1/portfolio", tags=["portfolio"])
    app.include_router(risk_router, prefix="/api/v1/risk", tags=["risk"])
    app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
    app.include_router(ws_router)

    # ── Health endpoint ───────────────────────────────────────────────────
    @app.get("/health", tags=["health"])
    async def health_check() -> dict:
        """Return service health with database status."""
        db_status = "disconnected"
        try:
            engine = create_async_engine(settings.DATABASE_URL, echo=False)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_status = "connected"
            await engine.dispose()
        except Exception:
            pass
        return {"status": "ok", "db": db_status}

    return app


# Module-level app instance for `uvicorn app.main:app`
app = create_app()
