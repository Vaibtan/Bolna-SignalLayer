"""Authentication API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserMe
from app.services.auth.service import authenticate_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> JSONResponse:
    """Authenticate and set an httpOnly cookie with the JWT."""
    settings = get_settings()
    client_ip = get_client_ip(request)
    token, _user = await authenticate_user(
        db, body.email, body.password, client_ip
    )

    response = JSONResponse(content=TokenResponse().model_dump())
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.AUTH_COOKIE_SECURE,
        path="/",
    )
    return response


@router.post("/logout")
async def logout() -> JSONResponse:
    """Clear the auth cookie."""
    response = JSONResponse(content={"detail": "Logged out."})
    response.delete_cookie(key="access_token", path="/")
    return response


@router.get("/me", response_model=UserMe)
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Return the current authenticated user's profile."""
    return current_user
