import logging
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded as SlowApiRateLimitExceeded

from src.exceptions import (
    AgentError,
    AuthError,
    GuardrailError,
    InsufficientPermission,
    NotAuthenticated,
    NotFound,
    RateLimitExceeded,
    ResearchJobError,
    ServiceError,
    UnprocessableEntity,
)


def register_global_error_handlers(app: FastAPI):
    app.add_exception_handler(
        NotAuthenticated,
        create_exception_handler(
            status.HTTP_401_UNAUTHORIZED,
            {"status": "failure", "message": "", "err_code": "not_authenticated"},
        ),
    )
    app.add_exception_handler(
        NotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "status": "failure",
                "message": "",
                "err_code": "not_found",
            },
        ),
    )

    app.add_exception_handler(
        InsufficientPermission,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "status": "failure",
                "message": "",
                "err_code": "insufficient_permission",
            },
        ),
    )

    app.add_exception_handler(
        UnprocessableEntity,
        create_exception_handler(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            initial_detail={
                "status": "failure",
                "message": "",
                "err_code": "unprocessable_entity",
            },
        ),
    )

    app.add_exception_handler(
        AuthError,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "status": "failure",
                "message": "",
                "err_code": "auth_error",
            },
        ),
    )

    app.add_exception_handler(
        RateLimitExceeded,
        create_exception_handler(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            initial_detail={
                "status": "failure",
                "message": "",
                "err_code": "rate_limit_exceeded",
            },
        ),
    )

    app.add_exception_handler(
        ServiceError,
        create_exception_handler(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            initial_detail={
                "status": "failure",
                "message": "",
                "err_code": "service_error",
            },
        ),
    )

    app.add_exception_handler(
        AgentError,
        create_exception_handler(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            initial_detail={
                "status": "failure",
                "message": "",
                "err_code": "agent_error",
            },
        ),
    )

    app.add_exception_handler(
        ResearchJobError,
        create_exception_handler(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            initial_detail={
                "status": "failure",
                "message": "",
                "err_code": "research_job_error",
            },
        ),
    )

    # Guardrail errors (422 Unprocessable Entity) — registering the base
    # class covers PromptInjectionError and OutputGuardrailError too,
    # since both inherit from GuardrailError and neither is normally
    # surfaced directly to the end user (handled inside the agent pipeline).
    app.add_exception_handler(
        GuardrailError,
        create_exception_handler(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            initial_detail={
                "status": "failure",
                "message": "",
                "err_code": "guardrail_error",
            },
        ),
    )

    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore

    app.add_exception_handler(Exception, internal_server_error_handler)

    app.add_exception_handler(SlowApiRateLimitExceeded, slowapi_rate_limit_handler)


async def slowapi_rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "status": "failure",
            "message": "Too many requests. Please slow down.",
            "err_code": "rate_limit_exceeded",
        },
    )


def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = exc.errors()
    modified_details = {}
    for error in details:
        field_name = error["loc"][-1]  # Get last element (field name)
        modified_details[field_name] = error["msg"]

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "status": "failure",
            "message": "Validation error",
            "err_code": "validation_error",
            "errors": modified_details,
        },
    )


def internal_server_error_handler(request, exc: Exception):

    logging.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={"status": "failure", "message": "Internal server error", "err_code": "internal_server_error"},
    )


def create_exception_handler(
    status_code: int, initial_detail: Any
) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # If the exception has a custom message, use it
        if hasattr(exc, "message") and exc.message:
            detail = initial_detail.copy()
            detail["message"] = exc.message
            return JSONResponse(content=detail, status_code=status_code)

        response_status_code = status_code
        if hasattr(exc, "status_code") and exc.status_code:
            response_status_code = getattr(exc, "status_code", status_code)

        return JSONResponse(content=initial_detail, status_code=response_status_code)

    return exception_handler