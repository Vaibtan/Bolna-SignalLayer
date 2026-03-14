"""Application exception types and FastAPI exception handlers."""

import structlog
from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


class SignalLayerError(Exception):
    """Base exception type for handled application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(SignalLayerError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed.") -> None:
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(SignalLayerError):
    """Raised when an authenticated user lacks required permissions."""

    def __init__(self, message: str = "Forbidden.") -> None:
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class NotFoundError(SignalLayerError):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str = "Resource not found.") -> None:
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class RateLimitError(SignalLayerError):
    """Raised when a client exceeds the allowed request rate."""

    def __init__(self, retry_after: int = 60) -> None:
        self.retry_after = retry_after
        super().__init__(
            f"Too many requests. Retry after {retry_after} seconds.",
            status.HTTP_429_TOO_MANY_REQUESTS,
        )


async def global_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unhandled exceptions with a standard 500 response."""
    logger.error(
        'unhandled_exception',
        path=request.url.path,
        method=request.method,
        error=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={'detail': 'Internal Server Error'},
    )


async def signal_layer_exception_handler(
    request: Request,
    exc: SignalLayerError,
) -> JSONResponse:
    """Handle expected application errors."""
    logger.info(
        'application_exception',
        path=request.url.path,
        method=request.method,
        error=exc.message,
        status_code=exc.status_code,
    )

    headers: dict[str, str] = {}
    if isinstance(exc, RateLimitError):
        headers["Retry-After"] = str(exc.retry_after)

    return JSONResponse(
        status_code=exc.status_code,
        content={'detail': exc.message},
        headers=headers or None,
    )
