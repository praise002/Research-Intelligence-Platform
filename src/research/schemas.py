from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.competitors.schemas import CompetitorSummary
from src.research.models import JobStatus, JobType


class ResearchTriggerCreate(BaseModel):
    """POST /research/trigger — on-demand report for one competitor."""

    competitor_id: UUID


class ResearchTriggerResponse(BaseModel):
    """
    Immediate acknowledgement returned by POST /research/trigger.
    The actual report is delivered by email when done.
    """

    job_id: UUID
    status: str  # always "pending" at creation
    message: str  # e.g. "Report started. You'll receive an email when it's ready."


class JobFilterParams(BaseModel):
    """
    Query parameters for GET /admin/logs.
    Used with FastAPI Depends() — all optional, stack as AND filters.
    """

    status: JobStatus | None = None
    job_type: JobType | None = None
    competitor_id: UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class JobRead(BaseModel):
    """GET /admin/logs — admin only."""

    id: UUID
    job_type: JobType
    status: JobStatus
    celery_task_id: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    competitor: CompetitorSummary
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)
