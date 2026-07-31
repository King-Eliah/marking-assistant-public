"""FastAPI application entrypoint."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
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

# The clients are served from a different origin in development (Vite on 5173,
# the API on 8000), so a browser sends a preflight before every non-simple
# request. Without this the preflight is answered 405 and the real request is
# never made — which surfaces in the client as a network error rather than an
# HTTP status, and so cannot be told apart from the server being down.
#
# `allow_credentials` is required because the refresh token is an httpOnly
# cookie. That in turn forbids a wildcard origin: the browser refuses the
# combination, and rightly, since it would let any site make authenticated
# calls on behalf of a signed-in user.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
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
