import logging
import sys
import structlog
from src.config import settings


def setup_logging() -> None:
    # Shared processors — run for every log event regardless of output
    shared_processors = [
        # Adds the log level name ("info", "error") to every event
        structlog.stdlib.add_log_level,

        # Adds the logger name (module path) to every event
        structlog.stdlib.add_logger_name,

        # Adds ISO 8601 timestamp to every event
        # e.g. "2026-05-07T14:30:00.123456Z"
        structlog.processors.TimeStamper(fmt="iso"),

        # If an exception was passed, format it as a string
        # so it appears in the JSON output rather than crashing the renderer
        structlog.processors.format_exc_info,

        # Converts all values to strings so the JSON renderer
        # does not choke on non-serializable types like UUIDs or datetimes
        structlog.processors.UnicodeDecoder(),
    ]

    # Choose renderer based on environment
    if settings.ENVIRONMENT == "production":
        # Production: JSON output
        # Each log line is a single JSON object — easy for log aggregators
        # to parse and index (Datadog, Grafana, Railway log search)
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: colorful console output
        # Much easier to read during local development
        # Shows level, timestamp, event name, and key-value pairs
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            # This must come last — converts the processed event dict
            # to the final output string (JSON or console)
            renderer,
        ],
        # Use standard library logging as the backend
        # This bridges structlog with uvicorn, FastAPI, SQLAlchemy logs
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging level
    # This affects uvicorn, httpx, and any library using stdlib logging
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",   # structlog handles formatting, not stdlib
        stream=sys.stdout,
        level=log_level,
    )

    # Silence overly verbose libraries in production
    if settings.ENVIRONMENT == "production":
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """
    Get a named structlog logger.

    USAGE:
        log = get_logger(__name__)
        log.info("event.name", key="value", another_key=123)

    WHY pass __name__?
    It records the module path (e.g. "src.chat.service") in every log
    line — makes it easy to trace which file produced which log.
    """
    return structlog.get_logger(name)

"""
USAGE:
  from src.custom_logging import get_logger
  log = get_logger(__name__)
  log.info("chat.request.received", user_id=uid, message_length=42)
  log.error("gemini.call.failed", error=str(e), attempt=2)
"""
