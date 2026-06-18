from fastapi import FastAPI, status

from src.auth.exceptions import (
    AccessTokenRequired,
    GoogleAuthenticationFailed,
    InvalidToken,
    NotAuthenticated,
    RefreshTokenRequired,
    RevokedToken,
    UserNotActive,
)
from src.errors import create_exception_handler


def register_auth_error_handlers(app: FastAPI):
    """
    Registers exception handlers for the authentication module.
    """
    app.add_exception_handler(
        NotAuthenticated,
        create_exception_handler(
            status.HTTP_401_UNAUTHORIZED,
            {"status": "failure", "message": "Not authenticated", "err_code": "unauthorized"},
        ),
    )
    app.add_exception_handler(
        InvalidToken,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "status": "failure",
                "message": "Invalid token or token expired",
                "err_code": "invalid_token",
            },
        ),
    )
    app.add_exception_handler(
        RevokedToken,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "status": "failure",
                "message": "Token is invalid or has been revoked",
                "err_code": "token_revoked",
            },
        ),
    )
    app.add_exception_handler(
        AccessTokenRequired,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "status": "failure",
                "message": "Please provide a valid access token",
                "err_code": "access_token_required",
            },
        ),
    )
    app.add_exception_handler(
        RefreshTokenRequired,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "status": "failure",
                "message": "Please provide a valid refresh token",
                "err_code": "refresh_token_required",
            },
        ),
    )
    app.add_exception_handler(
        UserNotActive,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "status": "failure",
                "message": "Your account has been disabled. Please contact support for assistance",
                "err_code": "forbidden",
            },
        ),
    )
    app.add_exception_handler(
        GoogleAuthenticationFailed,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "status": "failure",
                "message": "Google authentication failed",
                "err_code": "google_auth_failed",
            },
        ),
    )
