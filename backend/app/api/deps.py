"""Reusable FastAPI dependency functions."""

from typing import Annotated

from fastapi import Cookie, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.models.user import User


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
