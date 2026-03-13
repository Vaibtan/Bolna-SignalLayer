"""FastAPI application entrypoint for the DealGraph backend."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Awaitable, Callable, cast

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.api.auth import router as auth_router
from app.core.config import get_settings
from app.core.exceptions import (
    DealGraphError,
    dealgraph_exception_handler,
    global_exception_handler,
)
from app.core.logging import setup_logging

logger = structlog.get_logger(__name__)
ExceptionHandler = Callable[[object, Exception], Response | Awaitable[Response]]


def _get_cors_origins() -> list[str]:
    """Return configured CORS origins without forcing full settings load."""
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    return [
        origin.strip()
        for origin in frontend_url.split(',')
        if origin.strip()
    ]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Run startup and shutdown hooks."""
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)
    logger.info('startup.initiated', environment=settings.ENVIRONMENT)
    yield
    logger.info('shutdown.initiated')


app = FastAPI(
    title='DealGraph Voice OS',
    description='Enterprise Voice AI and revenue intelligence platform.',
    version='1.0.0',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(
    DealGraphError,
    cast(ExceptionHandler, dealgraph_exception_handler),
)

app.include_router(auth_router)


@app.get('/api/health/live', tags=['health'])
async def health_live() -> dict[str, str]:
    """Return a liveness response."""
    return {'status': 'ok'}


@app.get('/api/health/ready', tags=['health'])
async def health_ready() -> dict[str, str]:
    """Return a readiness response."""
    return {'status': 'ok'}
