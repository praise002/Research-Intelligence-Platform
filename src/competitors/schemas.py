from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from src.competitors.models import SourceType


class CompetitorBase(BaseModel):
    name: str
    main_url: str


class CompetitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    main_url: str = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be blank")
        return v.strip()

    @field_validator("main_url")
    @classmethod
    def clean_and_validate_url(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if not v:
            raise ValueError("URL cannot be blank")
        # Add https:// if no scheme provided so grey.com becomes https://grey.com
        if not v.startswith(("http://", "https://")):
            v = f"https://{v}"
        # Validate it's actually a URL
        try:
            HttpUrl(v)
        except Exception:
            raise ValueError("Please provide a valid URL e.g. grey.com or https://grey.com")
        return v



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
    sources: list[CompetitorSourceRead] 

    model_config = ConfigDict(from_attributes=True)
