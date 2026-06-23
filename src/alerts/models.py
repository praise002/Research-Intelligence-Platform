import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlmodel import Column, DateTime, Field, Relationship, SQLModel, func

from src.db.db_naming import metadata

if TYPE_CHECKING:
    from src.auth.models import User
    from src.competitors.models import Competitor

SQLModel.metadata = metadata

class Alert(SQLModel, table=True):
    """
    A real-time signal detected for one competitor — e.g. a pricing change.
    Created by alert_task.py when a delta against the last report baseline
    crosses the significance threshold.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    user: "User | None" = Relationship(back_populates="alerts")

    competitor_id: uuid.UUID = Field(foreign_key="competitor.id", index=True)
    competitor: "Competitor | None" = Relationship(back_populates="alerts")

    signal_type: str  # "pricing" | "feature" | "news" | "social"
    content: str  # short summary of what changed
    delivered_at: datetime | None = None  # set when the alert email / push is sent
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )