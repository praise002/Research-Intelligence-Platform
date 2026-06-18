import enum
import uuid
from datetime import datetime, timezone

from pydantic import EmailStr
from sqlalchemy import Column, DateTime, String, func
from sqlmodel import Field, SQLModel


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
    company: str = Field(max_length=50, min_length=1)
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    google_id: str | None = Field(
        sa_column=Column(String(50), unique=True), default=None
    )
    auth_provider: str | None = Field(max_length=50, default=None, nullable=True)
    is_active: bool = True
    is_superuser: bool = False
    role: UserRole = Field(default=UserRole.user)
    plan: UserPlan = Field(default=UserPlan.free)

    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    # created_at: datetime | None = Field(
    #     default_factory=get_datetime_utc,
    #     sa_type=DateTime(timezone=True)
    # )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),  # Database-side default
            onupdate=func.now(),
            nullable=False,
        ),
    )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return self.full_name
