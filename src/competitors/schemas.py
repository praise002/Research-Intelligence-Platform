from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.competitors.models import SourceType


class CompetitorBase(BaseModel):
    name: str
    main_url: str


class CompetitorCreate(CompetitorBase):
    pass


class CompetitorUpdate(BaseModel):
    name: str | None = None
    main_url: str | None = None


class CompetitorSourceRead(BaseModel):
    """Embedded inside CompetitorRead. Not a standalone endpoint."""

    id: UUID
    url: str
    source_type: SourceType
    last_scraped_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompetitorSummary(BaseModel):
    """
    Lightweight read — used in list responses and embedded in
    AlertSummary, AlertRead, ReportSummary, ReportRead, JobRead.
    """

    id: UUID
    name: str
    main_url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompetitorRead(CompetitorBase):
    """GET /competitors/{id} — full detail with discovered sources."""

    id: UUID
    created_at: datetime
    sources: list[CompetitorSourceRead] = []

    model_config = ConfigDict(from_attributes=True)
