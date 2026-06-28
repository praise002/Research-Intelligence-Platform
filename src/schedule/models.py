import enum
import uuid
from datetime import datetime, time
from typing import TYPE_CHECKING, Optional

from sqlmodel import Column, DateTime, Field, Relationship, SQLModel, func

from src.db.db_naming import metadata

if TYPE_CHECKING:
    from src.auth.models import User

SQLModel.metadata = metadata

class ScheduleFrequency(str, enum.Enum):
    weekly = "weekly"
    daily = "daily"


class ScheduleStatus(str, enum.Enum):
    active = "active"
    paused = "paused"

class Schedule(SQLModel, table=True):
    """
    A user's research cadence settings. One schedule covers all of that
    user's competitors — a single job researches every competitor on
    the user's list in parallel (Section 2 — staggered Celery tasks).
    updated_at matters here specifically for debugging: if a user pauses
    on Wednesday and asks why Monday's report didn't arrive, this field
    is the audit trail.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    user_id: uuid.UUID = Field(foreign_key="user.id", unique=True, ondelete="CASCADE")
    
    user: Optional["User"] = Relationship(
        back_populates="schedule",
    )

    frequency: ScheduleFrequency = Field(default=ScheduleFrequency.weekly)  # "weekly" | "daily"
    day_of_week: str | None = Field(default="Monday")  # used when frequency == "weekly"
    scheduled_time: time = Field(default=time(8, 0))  # e.g. 08:00
    timezone: str = Field(default="UTC")  # e.g. "Africa/Lagos", "Europe/London"
    status: ScheduleStatus = Field(default=ScheduleStatus.active)  # "active" | "paused"
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        ),
    )