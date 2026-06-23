"""
Shared pagination — used by GET /reports, GET /alerts, GET /admin/logs
(every list endpoint defined in Section 13's API list).

USAGE (e.g. in src/reports/router.py):

    from typing import Annotated
    from fastapi import Depends
    from src.utils.pagination import PaginationParams, PaginatedResponse

    @router.get("/reports", response_model=PaginatedResponse[ReportResponse])
    async def list_reports(
        pagination: Annotated[PaginationParams, Depends()],
        ...
    ):
        reports = await repo.get_all_by_user(user_id, pagination.skip, pagination.limit)
        total = await repo.count_by_user(user_id)
        return PaginatedResponse.build(items=reports, total=total, pagination=pagination)
"""

from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """
    Query params shared by every paginated list endpoint.
    FastAPI's Depends() instantiates this directly from ?skip=&limit=
    on the request, so routers never parse these by hand.
    """

    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=20, ge=1, le=100, description="Max records to return, capped at 100")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic envelope wrapping any list response with pagination metadata."""

    items: list[T]
    total: int
    skip: int
    limit: int
    has_more: bool

    @classmethod
    def build(cls, items: list[T], total: int, pagination: PaginationParams) -> "PaginatedResponse[T]":
        """
        Builds the response envelope from raw query results.
        has_more tells the frontend whether to show a "load more" button
        without it having to do the skip + limit < total arithmetic itself.
        """
        return cls(
            items=items,
            total=total,
            skip=pagination.skip,
            limit=pagination.limit,
            has_more=(pagination.skip + pagination.limit) < total,
        )