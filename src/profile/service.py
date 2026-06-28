from src.exceptions import NotFound
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.models import User
from src.profile.repository import ProfileRepository
from src.profile.schemas import ProfileResponse, ProfileUpdate

_repo = ProfileRepository()


class ProfileService:
    """
    Business logic for the profile module.
    """

    async def get_profile(self, user_id: uuid.UUID, session: AsyncSession) -> ProfileResponse:
        """
        Fetches the user's profile and returns it as a ProfileResponse.
        Raises ProfileNotFound if the user doesn't exist — in practice
        this only fires if the user was deleted between auth and this call.
        """
        user = await _repo.get_by_user_id(user_id, session)
        if not user:
            raise NotFound("Profile not found")
        return ProfileResponse.model_validate(user)

    async def update_profile(
        self, user: User, updates: ProfileUpdate, session: AsyncSession
    ) -> ProfileResponse:
        """
        Applies only the fields the user sent (exclude_unset strips the rest).
        Returns the updated profile as a ProfileResponse.
        """
        data = updates.model_dump(exclude_unset=True)
        updated_user = await _repo.update_profile(user, data, session)
        return ProfileResponse.model_validate(updated_user)