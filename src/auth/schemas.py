
from typing import Self

from pydantic import BaseModel, EmailStr, field_validator, model_validator

ACCESS_TOKEN_EXAMPLE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzMxMDY5NzEyLCJpYXQiOjE3MzA5ODMzMTIsImp0aSI6ImIzYTM2NmEwMDZkZTQxZTg4YzRlNDhmNzZmYmYyNWQ0IiwidXNlcl9pZCI6IjNhYzFlMzJiLTUzOWYtNDZkYi05ODZlLWRiZDFkZDQyYmUzMCIsInVzZXJuYW1lIjoiZGF2aWQtYmFkbXVzIn0.YuhFA2m47oDiwkOUd359hcumhN6lX5QfvXd92ES8vSQ"
REFRESH_TOKEN_EXAMPLE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTczODc1OTMxMiwiaWF0IjoxNzMwOTgzMzEyLCJqdGkiOiI5NjBkZmE2NTFhYjk0YWYzYTU4MjgzMTcwYjIxODEwYiIsInVzZXJfaWQiOiIzYWMxZTMyYi01MzlmLTQ2ZGItOTg2ZS1kYmQxZGQ0MmJlMzAiLCJ1c2VybmFtZSI6ImRhdmlkLWJhZG11cyJ9.A5shgQ-SI891PRS6nDs4-LA6ZNBoVXmLF2L9VMXoPC4"
FAILURE_EXAMPLE = "failure"

class UserBase(BaseModel):
    first_name: str 
    last_name: str 
    email: EmailStr

    @field_validator("email", mode="after")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()

    @model_validator(mode="after")
    def validate(self) -> Self:
        if len(self.first_name.split()) > 1 or len(self.last_name.split()) > 1:
            raise ValueError("No spacing allowed")

        return self

class UserCreateOAuth(UserBase):
    auth_provider: str | None = None
    google_id: str | None = None
    
