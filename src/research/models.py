import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Column, DateTime, Field, Relationship, SQLModel, func

from src.db.db_naming import metadata

if TYPE_CHECKING:
    from src.auth.models import User
    from src.competitors.models import Competitor

SQLModel.metadata = metadata

class JobType(str, enum.Enum):
    scheduled = "scheduled"
    on_demand = "on_demand"
    alert_scan = "alert_scan"

class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"

class Job(SQLModel, table=True):
    """
    A single research run for one competitor — scheduled, on-demand,
    or an alert scan. id is the correlation ID used across LangSmith,
    Sentry, and Structlog for tracing (see docs/EVALUATION.md).
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    user_id: uuid.UUID = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    user: "User | None" = Relationship(back_populates="jobs")

    competitor_id: uuid.UUID = Field(foreign_key="competitor.id", index=True, ondelete="CASCADE")
    competitor: "Competitor | None" = Relationship(back_populates="jobs")

    job_type: JobType = Field(default=JobType.scheduled)  # "scheduled" | "on_demand" | "alert_scan"  (WF1 / WF2 / WF3)
    status: JobStatus = Field(default=JobStatus.pending)  # "pending" | "running" | "completed" | "failed"
    celery_task_id: str | None = None  # for cross-referencing in Flower dashboard
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    