import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pydantic import EmailStr
from sqlalchemy import Column, DateTime, String, func
from sqlmodel import Field, Relationship, SQLModel

from src.db.db_naming import metadata

if TYPE_CHECKING:
    from src.alerts.models import Alert
    from src.competitors.models import Competitor
    from src.reports.models import Feedback, Report
    from src.research.models import Job
    from src.schedule.models import Schedule

SQLModel.metadata = metadata


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class UserPlan(str, enum.Enum):
    free = "free"
    paid = "paid"


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    first_name: str = Field(max_length=50, min_length=1)
    last_name: str = Field(max_length=50, min_length=1)
    company: str | None = Field(default=None, max_length=50)
    email: EmailStr = Field(unique=True, max_length=255)
    google_id: str | None = Field(
        sa_column=Column(String(50), unique=True), default=None
    )
    auth_provider: str | None = Field(max_length=50, default=None, nullable=True)
    is_active: bool = True
    is_admin: bool = False
    role: UserRole = Field(default=UserRole.user)
    plan: UserPlan = Field(default=UserPlan.free)

    # one-to-many — cascade lives here, on the "one" side
    competitors: list["Competitor"] | None = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    reports: list["Report"] | None = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    feedback: list["Feedback"] | None = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    alerts: list["Alert"] | None = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    jobs: list["Job"] | None = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    schedule: "Schedule | None" = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "uselist": False,
        },
    )

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

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return self.full_name