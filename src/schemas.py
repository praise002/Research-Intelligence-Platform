from pydantic import BaseModel


class ErrorResponse(BaseModel):
    status: str = "failure"
    message: str
    err_code: str
    
class ValidationErrorResponse(BaseModel):
    status: str = "failure"
    message: str = "Validation error"
    err_code: str = "validation_error"
    errors: dict[str, str]  # {"name": "String should have at least 1 character"}