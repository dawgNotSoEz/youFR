from __future__ import annotations

from fastapi import FastAPI

from ai_hall.api.routes import router
from ai_hall.config import get_settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Truth Layer",
        version="0.3.0",
        description="Verification infrastructure for AI systems: claim extraction, evidence retrieval, hallucination detection, explainability, and trust scoring.",
    )
    if get_settings().dashboard_enabled:
        from ai_hall.api.dashboard import router as dashboard_router

        app.include_router(dashboard_router)
    app.include_router(router)
    return app


app = create_app()

