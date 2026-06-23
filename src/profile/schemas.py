from src.auth.models import UserRole
from src.auth.models import UserPlan
from datetime import datetime
import uuid
from typing import Self

from pydantic import BaseModel, Field, model_validator, ConfigDict

from src.auth.schemas import UserBase

class UserUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=50)
    last_name: str | None = Field(default=None, min_length=1, max_length=50)
    company: str | None = Field(default=None, min_length=1, max_length=50)
    
    @model_validator(mode="after")
    def validate_names(self) -> Self:
        if self.first_name is not None and len(self.first_name.split()) > 1:
            raise ValueError("No spacing allowed in first_name")
        if self.last_name is not None and len(self.last_name.split()) > 1:
            raise ValueError("No spacing allowed in last_name")
        return self

class UserRead(UserBase):
    id: uuid.UUID
    company: str | None 
    role: UserRole
    plan: UserPlan
    created_at: datetime
    
    
    model_config = ConfigDict(from_attributes=True)