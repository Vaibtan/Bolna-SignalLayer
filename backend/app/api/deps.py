"""Reusable FastAPI dependency functions."""

from typing import Annotated

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.models.user import User


def get_client_ip(request: Request) -> str:
    """Return the best available client IP.

    Respects X-Forwarded-For / X-Real-IP when the
    TRUST_PROXY_HEADERS setting is enabled.
    """
    settings = get_settings()
    if settings.TRUST_PROXY_HEADERS:
        forwarded_for = request.headers.get(
            "x-forwarded-for",
        )
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

    if request.client is not None:
        return request.client.host

    return "unknown"


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    access_token: Annotated[str | None, Cookie()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Extract and validate JWT from cookie or Authorization header."""
    token: str | None = access_token

    if token is None and authorization is not None:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer" and value:
            token = value

    if token is None:
        raise AuthenticationError("Not authenticated.")

    try:
        claims = decode_access_token(token)
    except Exception as exc:
        raise AuthenticationError("Invalid or expired token.") from exc

    user_id = claims.get("sub")
    if user_id is None:
        raise AuthenticationError("Invalid token claims.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthenticationError("User not found.")

    return user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the current user has admin role."""
    if current_user.role != "admin":
        raise AuthorizationError("Admin access required.")
    return current_user
