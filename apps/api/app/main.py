"""FastAPI application entrypoint.

Scaffold only. No engine, model, or business logic lives here yet — see
docs/TASKS.md for what lands next (stage 1, the platform spine).
"""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.core.config import Settings, get_settings

app = FastAPI(
    title="Marking Assistant API",
    version="0.1.0",
    docs_url="/docs",
)


class Health(BaseModel):
    """Liveness response."""

    status: Literal["ok"]
    env: str
    pipeline_version: str


@app.get("/healthz", response_model=Health, tags=["ops"])
def healthz() -> Health:
    """Liveness probe. Does not touch the database or any external provider."""
    settings: Settings = get_settings()
    return Health(
        status="ok",
        env=settings.app_env,
        pipeline_version=settings.pipeline_version,
    )
