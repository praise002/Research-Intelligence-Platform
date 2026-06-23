from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.competitors.schemas import CompetitorSummary


class AlertSummary(BaseModel):
    """GET /alerts (list) — content truncated to 120 chars in the endpoint."""

    id: UUID
    signal_type: str
    content: str 
    delivered_at: datetime | None
    created_at: datetime
    competitor: CompetitorSummary

    model_config = ConfigDict(from_attributes=True)


class AlertRead(BaseModel):
    """GET /alerts/{id} — full content."""

    id: UUID
    signal_type: str
    content: str
    delivered_at: datetime | None
    created_at: datetime
    competitor: CompetitorSummary

    model_config = ConfigDict(from_attributes=True)
