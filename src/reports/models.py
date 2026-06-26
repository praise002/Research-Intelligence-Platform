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

class ReportStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"

class Report(SQLModel, table=True):
    """
    A generated competitive intelligence report for one competitor.

    quality_score: internal LLM-as-judge score (Gemini 2.5 Flash evaluator).
    NOT shown to the user — used for the >=4.0 deliver / <4.0 refine gate
    and for flagging reports below 4.0 for human review.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    user_id: uuid.UUID = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    # many-side — no cascade kwarg; cascade lives on User.reports
    user: "User | None" = Relationship(back_populates="reports")

    competitor_id: uuid.UUID = Field(foreign_key="competitor.id", index=True, ondelete="CASCADE")
    # many-side — no cascade kwarg; cascade lives on Competitor.reports
    competitor: "Competitor | None" = Relationship(back_populates="reports")

    content: str  # full report in markdown — SWOT, trends, executive summary
    quality_score: float | None = None
    sources_count: int = Field(default=0)
    status: ReportStatus = Field(default=ReportStatus.pending)

    # one-to-one — cascade lives here, since Report is the "owning" side
    feedback: "Feedback | None" = Relationship(
        back_populates="report",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "uselist": False},
    )

    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    delivered_at: datetime | None = None


class Feedback(SQLModel, table=True):
    """
    User-submitted star rating on a report. One feedback per report
    (RPT_002 raised on duplicate submission attempt).
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    report_id: uuid.UUID = Field(foreign_key="report.id", unique=True, ondelete="CASCADE")
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    rating: int = Field(ge=1, le=5) # 1-5 stars
    comment: str | None = None  # optional — "what did we miss?"

    report: "Report | None" = Relationship(back_populates="feedback")
    user: "User | None" = Relationship(back_populates="feedback")

    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )