"""Application configuration helpers and typed settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from environment variables.

    Attributes:
        ENVIRONMENT: Runtime environment name such as ``local`` or ``test``.
        LOG_LEVEL: Application log level for stdlib and structlog output.
        DB_ECHO: Whether SQLAlchemy should log SQL statements.
        DATABASE_URL: Async SQLAlchemy database connection string.
        REDIS_URL: Redis connection string for queues and caching.
        REDIS_RATE_LIMIT_PREFIX: Redis key prefix for rate limit state.
        JWT_SECRET: Secret used to sign authentication tokens.
        AUTH_MAX_FAILED_ATTEMPTS: Maximum failed login attempts before lockout.
        AUTH_LOCKOUT_WINDOW_SECONDS: Lockout duration after too many failures.
        AUTH_COOKIE_SECURE: Whether the auth cookie requires HTTPS transport.
        TRUST_PROXY_HEADERS: Whether forwarded client IP headers are trusted.
        FRONTEND_URL: Allowed browser origin for the frontend application.
        NEXT_PUBLIC_API_URL: Public API base URL used by the frontend.
        NEXT_PUBLIC_WS_URL: Public WebSocket URL used by the frontend.
        NEXT_PUBLIC_ACTIVE_STATE_POLL_INTERVAL_MS: Poll interval for active UI
            states when WebSockets are unavailable.
        BOLNA_API_KEY: API key for Bolna outbound call requests.
        BOLNA_AGENT_ID: Default Bolna agent identifier.
        BOLNA_MOCK_MODE: Whether to stub Bolna integration in local testing.
        BOLNA_EXECUTION_POLL_INTERVAL_SECONDS: Poll interval for execution
            fallback checks.
        BOLNA_EXECUTION_POLL_MAX_ATTEMPTS: Max attempts for execution polling.
        BOLNA_WEBHOOK_ALLOWED_IPS: Optional comma-separated webhook allowlist.
        WEBHOOK_BASE_URL: Public webhook base URL for provider callbacks.
        WEBHOOK_MAX_BODY_SIZE_MB: Maximum accepted webhook payload size.
        WEBHOOK_IDEMPOTENCY_TTL_SECONDS: TTL for webhook idempotency keys.
        GEMINI_API_KEY: API key for Google Gemini calls.
        GEMINI_MODEL_EXTRACTION: Model used for extraction and risk analysis.
        GEMINI_MODEL_RECOMMENDATION: Model used for recommendation drafting.
        GEMINI_MODEL_EMBEDDING: Model used for vector embedding generation.
        LLM_MAX_CONCURRENT_REQUESTS: Max concurrent LLM requests per process.
        LLM_VALIDATION_MAX_RETRIES: Repair retries for structured outputs.
        CALL_INIT_MAX_PER_USER_WINDOW: Per-user call initiation quota window.
        CALL_INIT_WINDOW_SECONDS: Duration of the per-user quota window.
        CALL_INIT_STAKEHOLDER_COOLDOWN_SECONDS: Cooldown before recalling a
            stakeholder.
        WORKER_MAX_CONCURRENT_PIPELINES: Max concurrent worker pipelines.
    """

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    ENVIRONMENT: str = 'local'
    LOG_LEVEL: str = 'INFO'
    DB_ECHO: bool = False

    DATABASE_URL: str
    REDIS_URL: str
    REDIS_RATE_LIMIT_PREFIX: str = 'dealgraph:ratelimit'
    JWT_SECRET: str

    AUTH_MAX_FAILED_ATTEMPTS: int = 5
    AUTH_LOCKOUT_WINDOW_SECONDS: int = 900
    AUTH_COOKIE_SECURE: bool = False
    TRUST_PROXY_HEADERS: bool = False

    FRONTEND_URL: str = 'http://localhost:3000'
    NEXT_PUBLIC_API_URL: str = 'http://localhost:8000'
    NEXT_PUBLIC_WS_URL: str = 'ws://localhost:8000'
    NEXT_PUBLIC_ACTIVE_STATE_POLL_INTERVAL_MS: int = 5000

    BOLNA_API_KEY: str = ''
    BOLNA_AGENT_ID: str = ''
    BOLNA_MOCK_MODE: bool = False
    BOLNA_EXECUTION_POLL_INTERVAL_SECONDS: int = 5
    BOLNA_EXECUTION_POLL_MAX_ATTEMPTS: int = 24
    BOLNA_WEBHOOK_ALLOWED_IPS: str = ''

    WEBHOOK_BASE_URL: str = ''
    WEBHOOK_MAX_BODY_SIZE_MB: int = 2
    WEBHOOK_IDEMPOTENCY_TTL_SECONDS: int = 86400

    GEMINI_API_KEY: str = ''
    GEMINI_MODEL_EXTRACTION: str = 'gemini-2.5-flash'
    GEMINI_MODEL_RECOMMENDATION: str = 'gemini-2.5-pro'
    GEMINI_MODEL_EMBEDDING: str = 'gemini-embedding-001'
    LLM_MAX_CONCURRENT_REQUESTS: int = 2
    LLM_VALIDATION_MAX_RETRIES: int = 2

    CALL_INIT_MAX_PER_USER_WINDOW: int = 3
    CALL_INIT_WINDOW_SECONDS: int = 600
    CALL_INIT_STAKEHOLDER_COOLDOWN_SECONDS: int = 300
    WORKER_MAX_CONCURRENT_PIPELINES: int = 2


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()  # type: ignore[call-arg]  # Loaded from environment.
