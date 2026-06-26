from fastapi import FastAPI

from src.auth.errors import register_auth_error_handlers
from src.competitors.errors import register_competitor_error_handlers
from src.errors import register_global_error_handlers


def register_all_error_handlers(app: FastAPI) -> None:
    register_auth_error_handlers(app)
    register_competitor_error_handlers(app)
    register_global_error_handlers(app)      # always last