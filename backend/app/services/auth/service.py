"""Authentication service with brute-force rate limiting."""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, RateLimitError
from app.core.redis import get_redis_client
from app.core.security import create_access_token, verify_password
from app.models.user import User

logger = structlog.get_logger(__name__)


def _rate_limit_key(email: str, ip: str) -> str:
    """Build the Redis key for auth throttling state.

    Callers must pass an already-normalized email (lowercase, stripped).
    """
    settings = get_settings()
    return (
        f'{settings.REDIS_RATE_LIMIT_PREFIX}:auth:login:'
        f'{email}:{ip}'
    )


async def _check_rate_limit(email: str, ip: str) -> None:
    """Raise RateLimitError if the email and IP pair is locked out."""
    settings = get_settings()
    redis = get_redis_client()
    key = _rate_limit_key(email, ip)
    count = await redis.get(key)
    if count is not None and int(count) >= settings.AUTH_MAX_FAILED_ATTEMPTS:
        ttl = await redis.ttl(key)
        logger.warning(
            "auth.brute_force_lockout",
            email=email,
            ip=ip,
            attempts=int(count),
            ttl=ttl,
        )
        raise RateLimitError(retry_after=max(ttl, 1))


async def _record_failed_attempt(email: str, ip: str) -> None:
    """Increment failed login tracking for the email and IP pair."""
    settings = get_settings()
    redis = get_redis_client()
    key = _rate_limit_key(email, ip)
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, settings.AUTH_LOCKOUT_WINDOW_SECONDS)
    await pipe.execute()


async def _clear_failed_attempts(email: str, ip: str) -> None:
    """Clear failed login tracking for the email and IP pair."""
    redis = get_redis_client()
    key = _rate_limit_key(email, ip)
    await redis.delete(key)


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
    client_ip: str,
) -> tuple[str, User]:
    """Authenticate a user, returning (token, user) on success."""
    normalized_email = email.strip().lower()
    await _check_rate_limit(normalized_email, client_ip)

    result = await db.execute(
        select(User).where(User.email == normalized_email)
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        await _record_failed_attempt(normalized_email, client_ip)
        logger.info(
            'auth.login_failed',
            email=normalized_email,
            ip=client_ip,
        )
        raise AuthenticationError("Invalid email or password.")

    await _clear_failed_attempts(normalized_email, client_ip)
    token = create_access_token(user.id, user.org_id, user.role)
    logger.info('auth.login_success', user_id=str(user.id), ip=client_ip)
    return token, user
