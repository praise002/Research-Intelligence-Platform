import time

from decouple import config
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware

from src.config import settings
from src.custom_logging import get_logger

log = get_logger(__name__)

SKIP_LOGGING_PATHS = {"/health", "/", "/api/v1/docs"}

def register_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log each HTTP request/response"""
        if request.url.path in SKIP_LOGGING_PATHS:
            return await call_next(request)
        
        start_time = time.perf_counter()
        request_id = getattr(request.state, "request_id", "unknown")
        user_id = getattr(request.state, "user_id", "unauthenticated")

        log.info(
            "request.received",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            user_id=user_id,
            client_ip=request.client.host if request.client else "unknown",
        )

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        log.info(
            "request.completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response

    app.add_middleware(
        SessionMiddleware,
        secret_key=config("SECRET_KEY"),
    )

    origins = settings.all_cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        # allow_methods=["*"],
        # allow_headers=["*"],
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        # allow_credentials=True,  # cross-origin for frontend
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", ".ngrok-free.app", "testserver"],
    )
