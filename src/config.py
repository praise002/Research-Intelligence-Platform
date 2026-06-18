import secrets
import warnings
from typing import Annotated, Any, ClassVar, Literal

from pydantic import AnyUrl, BeforeValidator, HttpUrl, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


def parse_cors(v: Any) -> list[str] | str:
    """
    Accepts CORS origins as a comma-separated string or a list.
    Needed because Railway injects env vars as strings, not lists.

    Example .env value: BACKEND_CORS_ORIGINS=http://localhost:3000,https://app.arcip.com
    """
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


def empty_to_none(v: Any) -> Any:
    """Converts empty strings to None — prevents Pydantic from treating '' as a valid URL."""
    if v == "" or v is None:
        return None
    return v


class Settings(BaseSettings):
    """
    Global configuration for Reve AI — Automated Research & Competitive Intelligence Platform.
    All values loaded from .env file. Never hardcode secrets here.
    """

    # ── Application 
    PROJECT_NAME: str = "Reve AI"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["local", "test", "production"] = "local"
    DOMAIN: str = "localhost"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    
    FRONTEND_CALLBACK_URL: str

    # ── Database 
    # Either provide DATABASE_URL directly or all POSTGRES_* variables.
    # model_validator below assembles DATABASE_URL from parts if not provided.
    DATABASE_URL: str | None = None
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_HOST: str | None = None
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str | None = None

    # ── Redis 
    # Used for both Celery broker and application caching.
    REDIS_URL: ClassVar[str] = "redis://redis:6379/0"

    # ── LLM APIs (via OpenRouter) 
    # All models accessed through OpenRouter — swap model by changing the string.
    OPENROUTER_API_KEY: str
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Model assignments — each role uses a different model for cost and quality
    SYNTHESIS_MODEL: str = "anthropic/claude-sonnet-4-6"       # merges sources, writes report
    EVALUATOR_MODEL: str = "google/gemini-2.5-flash"           # grades report (cross-model)
    ROUTER_MODEL: str = "anthropic/claude-haiku-4-5"           # classifies request type (fast + cheap)
    QUERY_GENERATOR_MODEL: str = "anthropic/claude-haiku-4-5"  # generates search queries
    FALLBACK_MODEL: str = "deepseek/deepseek-chat"             # fallback if primary models fail

    # Model parameters
    TEMPERATURE: float = 0.3          # lower = more consistent, less creative (good for research)
    MAX_TOKENS: int = 4096            # max output tokens per synthesis call
    MAX_TOKENS_SUMMARY: int = 512     # max tokens for per-source summarisation (Haiku, cheaper)

    # ── Data Collection APIs 
    TAVILY_API_KEY: str               # primary search + extract + sub-URL discovery
    SERPER_API_KEY: str               # fallback when Tavily fails
    APIFY_API_KEY: str                # social media — X, Reddit, LinkedIn scrapers

    # ── Email Delivery 
    RESEND_API_KEY: str               # transactional email for report and alert delivery
    RESEND_FROM_EMAIL: str = "reports@reve.com"

    # ── Retry Configuration (Tenacity) 
    LLM_RETRY_COUNT: int = 3
    LLM_RETRY_MIN_WAIT: int = 1       # seconds — exponential backoff: 1s → 2s → 4s
    LLM_RETRY_MAX_WAIT: int = 16

    TAVILY_RETRY_COUNT: int = 3
    TAVILY_RETRY_MIN_WAIT: int = 1
    TAVILY_RETRY_MAX_WAIT: int = 16

    APIFY_RETRY_COUNT: int = 2
    APIFY_RETRY_MIN_WAIT: int = 2
    APIFY_RETRY_MAX_WAIT: int = 8

    # ── Timeouts (seconds) 
    LLM_TIMEOUT: int = 60             # synthesis can take up to 60s for large source sets
    TAVILY_TIMEOUT: int = 30
    APIFY_TIMEOUT: int = 45

    # ── Research Agent Configuration 
    MAX_RESEARCH_LOOPS: int = 3       # LangGraph loop limit — refine query max 3 times
    MAX_EVAL_RETRIES: int = 2         # evaluator-optimizer retry limit before delivering as-is
    MIN_SOURCE_COUNT: int = 5         # below this → add confidence warning to report
    TARGET_SOURCE_COUNT: int = 15     # target number of validated sources per report
    QUALITY_SCORE_THRESHOLD: float = 4.0   # below this → evaluator triggers refine
    MIN_REPORT_WORDS: int = 500       # output guardrail — below this → retry
    SOURCE_DEDUP_THRESHOLD: float = 0.92   # pgvector cosine similarity — above this → discard as duplicate
    CREDIBILITY_SCORE_THRESHOLD: float = 0.5  # source validator — below this → discard

    # ── Caching TTLs (seconds) 
    NEWS_CACHE_TTL: int = 86_400      # 24 hours — news and social data changes daily
    WEBSITE_CACHE_TTL: int = 604_800  # 7 days — pricing pages rarely change overnight
    SEMANTIC_CACHE_TTL: int = 86_400  # 24 hours — similar queries return cached result

    # ── Rate Limiting 
    ON_DEMAND_JOBS_PER_DAY: int = 10  # max manual research triggers per user per day

    # ── Scheduling 
    SCHEDULE_GROUP_SIZE: int = 10     # companies per stagger group
    SCHEDULE_GROUP_INTERVAL_MINUTES: int = 5  # minutes between each group

    # ── Cost Monitoring 
    MONTHLY_BUDGET_USD: float = 500.0
    COST_ALERT_THRESHOLD: float = 400.0   # alert at 80% of monthly budget

    # ── Observability 
    LOG_LEVEL: str = "INFO"
    LANGCHAIN_TRACING_V2: bool = False     # set True in staging/prod to enable LangSmith
    LANGCHAIN_API_KEY: str = ""            # LangSmith API key
    LANGCHAIN_PROJECT: str = "Reve AI"
    SENTRY_DSN: Annotated[HttpUrl | None, BeforeValidator(empty_to_none)] = None

    # ── CORS 
    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field
    @property
    def all_cors_origins(self) -> list[str]:
        """Returns CORS origins as clean strings without trailing slashes."""
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS]

    # ── Validators 

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        """Warn in local, raise in production if a secret is still set to the default."""
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis". '
                "Please change it before deploying."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        return self

    @model_validator(mode="after")
    def _assemble_db_url(self) -> Self:
        """
        Assembles DATABASE_URL from individual POSTGRES_* parts if not provided directly.
        Railway provides individual parts; direct DATABASE_URL is used for local dev.
        """
        if self.DATABASE_URL is None:
            if all([
                self.POSTGRES_USER,
                self.POSTGRES_PASSWORD,
                self.POSTGRES_HOST,
                self.POSTGRES_DB,
            ]):
                self.DATABASE_URL = (
                    f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                    f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
                )
            else:
                raise ValueError(
                    "Provide either DATABASE_URL or all POSTGRES_* variables."
                )
        return self

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()  # type: ignore

# ── Celery config 
# Exported here so celery_app.py can import without circular dependency.
broker_url = settings.REDIS_URL
result_backend = settings.REDIS_URL
broker_connection_retry_on_startup = True