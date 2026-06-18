from src.auth.schemas import (
    ACCESS_TOKEN_EXAMPLE,
    FAILURE_EXAMPLE,
    REFRESH_TOKEN_EXAMPLE,
)

VALIDATION_ERROR = {
    "value": {"detail": [{"loc": ["string", 0], "msg": "string", "type": "string"}]},
}

UNAUTHORIZED = {
    "content": {
        "application/json": {
            "example": {
                "status": FAILURE_EXAMPLE,
                "message": "Please provide a valid access token.",
                "err_code": "access_token_required",
            }
        }
    }
}

REFRESH_TOKEN_RESPONSES = {
    200: {
        "content": {
            "application/json": {
                "example": {
                    "message": "Token refreshed successfully",
                    "access_token": ACCESS_TOKEN_EXAMPLE,
                    "refresh_token": REFRESH_TOKEN_EXAMPLE,
                }
            }
        }
    },
    401: {
        "content": {
            "application/json": {
                "example": {
                    "status": "failure",
                    "message": "Invalid token or token expired.",
                    "resolution": "Please get a new token",
                    "error_code": "invalid_token",
                }
            }
        },
    },
}

LOGOUT_RESPONSES = {
    200: {
        "content": {
            "application/json": {
                "example": {
                    "status": "success",
                    "message": "Logged Out successfully",
                }
            }
        }
    },
    401: {
        "content": {
            "application/json": {
                "example": {
                    "status": "failure",
                    "message": "Please provide a valid refresh token.",
                    "resolution": "Please get a refresh token",
                    "error_code": "refresh_token_required",
                }
            }
        }
    },
}

LOGOUT_ALL_RESPONSES = {
    200: {
        "content": {
            "application/json": {
                "example": {
                    "message": "Logged out of all devices successfully",
                }
            }
        },
    },
    401: {
        "content": {
            "application/json": {
                "example": {
                    "status": "failure",
                    "message": "Please provide a valid access token.",
                    "resolution": "Please get an access token",
                    "err_code": "access_token_required",
                }
            }
        },
    },
}


# NOTE: DOCS SHOWS 422 BY DEFAULT IF THERE IS A 422 ERROR FOR EXAMPLES
