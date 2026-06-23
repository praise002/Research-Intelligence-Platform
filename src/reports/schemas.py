from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.competitors.schemas import CompetitorSummary
from src.reports.models import ReportStatus


class FeedbackCreate(BaseModel):
    """POST /reports/{id}/feedback"""

    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class FeedbackRead(BaseModel):
    """GET /reports/{id}/feedback — embedded inside ReportRead."""

    id: UUID
    rating: int
    comment: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportSummary(BaseModel):
    """GET /reports (list) — no markdown content."""

    id: UUID
    status: ReportStatus
    sources_count: int
    created_at: datetime
    delivered_at: datetime | None
    competitor: CompetitorSummary

    model_config = ConfigDict(from_attributes=True)


class ReportRead(BaseModel):
    """GET /reports/{id} — full report with markdown + embedded feedback."""

    id: UUID
    status: ReportStatus
    sources_count: int
    content: str
    created_at: datetime
    delivered_at: datetime | None
    competitor: CompetitorSummary
    feedback: FeedbackRead | None

    model_config = ConfigDict(from_attributes=True)
