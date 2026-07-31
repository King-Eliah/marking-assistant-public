"""FastAPI application entrypoint."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.db import assert_rls_applies
from app.core.scope import NotFoundError
from app.routers import auth, booklets, courses

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Fail fast on a configuration that would disable tenant isolation.

    Starting and serving traffic with RLS inert is worse than not starting:
    every request succeeds, so the fault surfaces only when one institution
    reads another's data.
    """
    del app
    try:
        assert_rls_applies()
    except Exception:
        logger.critical("refusing to start: tenant isolation is not in force")
        raise
    yield


app = FastAPI(
    title="Marking Assistant API",
    version="0.1.0",
    docs_url="/docs",
    lifespan=lifespan,
)


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    """Every `NotFoundError` becomes a bare 404.

    The body deliberately carries no entity type or id. Echoing "course
    <uuid> not found" back would confirm the shape of what was asked for,
    which is the enumeration leak `require_owned` exists to close.
    """
    del request, exc
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Not found"},
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


app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(booklets.router)
