import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlmodel import Column, DateTime, Field, Relationship, SQLModel, func

from src.db.db_naming import metadata

if TYPE_CHECKING:
    from src.alerts.models import Alert
    from src.auth.models import User
    from src.reports.models import Report
    from src.research.models import Job

SQLModel.metadata = metadata

class SourceType(str, enum.Enum):
    website = "website"
    social = "social"
    news = "news"
    review = "review"

class Competitor(SQLModel, table=True):
    """A competitor the user has added to track. One user can add many."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", index=True, ondelete="CASCADE"
    )
    # many-side — no cascade kwarg here; cascade lives on User.competitors
    user: Optional["User"] = Relationship(back_populates="competitors")

    name: str = Field(min_length=1, max_length=50)  # e.g. "Grey"
    main_url: str = Field(min_length=1)  # e.g. "grey.com" — provided by user at onboarding

    competitor_sources: list["CompetitorSource"] | None = Relationship(
        back_populates="competitor",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    reports: list["Report"] | None = Relationship(
        back_populates="competitor",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    alerts: list["Alert"] | None = Relationship(
        back_populates="competitor",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    jobs: list["Job"] | None = Relationship(
        back_populates="competitor",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )


class CompetitorSource(SQLModel, table=True):
    """
    A specific page discovered for a competitor — e.g. "grey.com/pricing".
    Populated by the sub-URL discovery service (Phase 6.3) after a
    competitor is added.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    competitor_id: uuid.UUID = Field(
        foreign_key="competitor.id", index=True, ondelete="CASCADE"
    )
    competitor: Optional["Competitor"] = Relationship(back_populates="competitor_sources")
    url: str
    source_type: SourceType  # "website" | "social" | "news" | "review"
    last_scraped_at: datetime | None = None  # set after each successful scrape
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )