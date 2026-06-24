"""
Repository Layer (Data Adapter)
================================
Implements all data access and mutation operations against the database.
Uses SQLModel/ORM only — no business logic, no HTTP concerns.

Dependency direction: inward only.
  - Imports from: domain/schemas, infrastructure/security
  - Must NOT import from: services, controllers, routers

Each public method maps to a CRUD operation or a focused query.
Complex orchestration (e.g. create user)
belongs in the service layer, not here.
"""
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.schemas import UserCreateOAuth
from src.db.models import User


class AuthRepository:
    """CRUD operations for the User model."""

    async def get_by_id(self, user_id: str, session: AsyncSession) -> User | None:
        statement = (
            select(User)
            .where(User.id == user_id)
        )
        result = await session.exec(statement)
        return result.first()

    async def get_by_email(self, email: str, session: AsyncSession) -> User | None:
        result = await session.exec(select(User).where(User.email == email))
        return result.first()



    async def create_oauth(
        self, user_data: UserCreateOAuth, session: AsyncSession
    ) -> User:
        """Create an OAuth user. Email is pre-verified by the provider."""
        new_user = User.model_validate(user_data)

        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

        return new_user

    async def update(
        self, user: User, data: dict, session: AsyncSession
    ) -> User:
        """Apply a partial update dict to a user and persist it."""
        for key, value in data.items():
            setattr(user, key, value)
        await session.commit()
        return user

    async def exists_by_email(self, email: str, session: AsyncSession) -> bool:
        return await self.get_by_email(email, session) is not None

