from fastapi import FastAPI, status

from src.competitors.exceptions import CompetitorAlreadyExists, SourceDiscoveryFailed
from src.errors import create_exception_handler


def register_competitor_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        CompetitorAlreadyExists,
        create_exception_handler(
            status_code=status.HTTP_409_CONFLICT,
            initial_detail={
                "status": "failure",
                "message": "",
                "err_code": "competitor_already_exists",
            },
        ),
    )

    app.add_exception_handler(
        SourceDiscoveryFailed,
        create_exception_handler(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            initial_detail={
                "status": "failure",
                "message": "",
                "err_code": "source_discovery_failed",
            },
        ),
    )