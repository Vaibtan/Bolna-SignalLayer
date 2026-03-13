"""Structured logging configuration for backend services."""

import logging
import sys
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response
from structlog.contextvars import bind_contextvars, clear_contextvars


def assign_request_id(
    request: Request,
) -> str:
    """Return the incoming request ID or generate a new one."""
    incoming = request.headers.get('x-request-id')
    if incoming:
        return incoming
    return str(uuid.uuid4())


async def request_context_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Bind a request ID to structured logs for the request lifecycle."""
    request_id = assign_request_id(request)
    clear_contextvars()
    bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )
    try:
        response = await call_next(request)
    finally:
        clear_contextvars()

    response.headers['X-Request-ID'] = request_id
    return response


def setup_logging(log_level: str = 'INFO') -> None:
    """Configure stdlib and structlog output for the application."""
    logging.basicConfig(
        format='%(message)s',
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
        force=True,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt='iso'),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
