from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.db.database import get_session
from src.profile.schemas import ProfileResponse, ProfileUpdate
from src.profile.service import ProfileService
from src.schemas import ErrorResponse, ValidationErrorResponse

router = APIRouter()

_service = ProfileService()


@router.get(
    "",
    response_model=ProfileResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Profile not found"},
    },
)
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProfileResponse:
    """Returns the authenticated user's profile."""
    return await _service.get_profile(current_user.id, session)


@router.patch(
    "",
    response_model=ProfileResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Profile not found"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
    },
)
async def update_profile(
    body: ProfileUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProfileResponse:
    """
    Partially updates the authenticated user's profile.
    Only fields included in the request body are changed.
    """
    return await _service.update_profile(current_user, body, session)