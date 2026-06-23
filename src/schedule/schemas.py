from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from src.schedule.models import ScheduleFrequency, ScheduleStatus


class ScheduleUpdate(BaseModel):
    """
    PATCH /schedule — all fields optional.
    Validation: day_of_week is rejected when frequency is 'daily'.
    """

    frequency: ScheduleFrequency | None = None
    day_of_week: str | None = None
    time: time | None = None
    timezone: str | None = None
    status: ScheduleStatus | None = None  # pause / resume

    @model_validator(mode="after")
    def reject_day_of_week_when_daily(self) -> "ScheduleUpdate":
        if self.frequency == ScheduleFrequency.daily and self.day_of_week is not None:
            raise ValueError("day_of_week must not be set when frequency is 'daily'")
        return self


class ScheduleRead(BaseModel):
    """GET /schedule — current settings for the authenticated user."""

    id: UUID
    frequency: ScheduleFrequency
    day_of_week: str | None
    time: time
    timezone: str
    status: ScheduleStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScheduleRunResponse(BaseModel):
    """
    POST /schedule/run-now — fires the same WF1 fan-out immediately.
    Returns one job_id per competitor in the user's list.
    """

    job_ids: list[UUID]
    status: str   # always "pending" at creation
    message: str  # e.g. "Research started for 3 competitors. You'll receive emails when done."
