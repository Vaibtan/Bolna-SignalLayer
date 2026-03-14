"""FastAPI application entrypoint for the Signal Layer OS backend."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Awaitable, Callable, cast

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.api.auth import router as auth_router
from app.api.calls import router as calls_router
from app.api.deals import router as deals_router
from app.api.intelligence import router as intelligence_router
from app.api.memory import router as memory_router
from app.api.stakeholders import router as stakeholders_router
from app.api.webhooks import router as webhooks_router
from app.api.ws import router as ws_router
from app.core.config import get_settings
from app.core.exceptions import (
    SignalLayerError,
    global_exception_handler,
    signal_layer_exception_handler,
)
from app.core.logging import (
    request_context_middleware,
    setup_logging,
)
from app.core.redis import close_redis_client
from app.services.bolna.adapter import close_bolna_adapter

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
    try:
        yield
    finally:
        await close_bolna_adapter()
        await close_redis_client()
        logger.info('shutdown.initiated')


app = FastAPI(
    title='Signal Layer OS',
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
app.middleware('http')(request_context_middleware)

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(
    SignalLayerError,
    cast(ExceptionHandler, signal_layer_exception_handler),
)

app.include_router(auth_router)
app.include_router(calls_router)
app.include_router(deals_router)
app.include_router(intelligence_router)
app.include_router(memory_router)
app.include_router(stakeholders_router)
app.include_router(webhooks_router)
app.include_router(ws_router)


@app.get('/api/health/live', tags=['health'])
async def health_live() -> dict[str, str]:
    """Return a liveness response."""
    return {'status': 'ok'}


@app.get('/api/health/ready', tags=['health'])
async def health_ready() -> dict[str, str]:
    """Return a readiness response."""
    return {'status': 'ok'}
