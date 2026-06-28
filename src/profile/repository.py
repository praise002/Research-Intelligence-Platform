import uuid
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import User


class ProfileRepository:

    async def get_by_user_id(self, user_id: uuid.UUID, session: AsyncSession) -> User | None:
        """Fetch a user by their UUID — returns None if not found."""
        statement = (
            select(User)
            .where(User.id == user_id)
        )
        result = await session.exec(statement)
        return result.first()

    async def update_profile(
        self, user: User, data: dict, session: AsyncSession
    ) -> User:
        """Apply a partial update dict to a user and persist it."""
        for key, value in data.items():
            setattr(user, key, value)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
