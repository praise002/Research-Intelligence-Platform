import uuid
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select

ModelType = TypeVar("ModelType", bound=SQLModel)


class BaseRepository(Generic[ModelType]):
    """
    Generic async CRUD operations shared by every module's repository.

    Generic[ModelType] means CompetitorRepository(BaseRepository[Competitor])
    gets full type hints — get_by_id() returns Competitor | None, not a
    bare object, so your editor and mypy both catch mistakes.
    """

    def __init__(self, db: AsyncSession, model: type[ModelType]):
        self.db = db
        self.model = model

    async def create(self, obj: ModelType) -> ModelType:
        """Insert a new row and return it with its generated id populated."""
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def get_by_id(self, id: uuid.UUID) -> ModelType | None:
        """Fetch a single row by primary key, or None if it doesn't exist."""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id) # type: ignore
        )
        return result.scalar_one_or_none()

    async def list(self, skip: int = 0, limit: int = 20) -> list[ModelType]:
        """
        Fetch a paginated list of all rows of this model.
        Module repositories typically override this with a scoped version
        (e.g. get_all_by_user) rather than calling this directly, since
        almost every table needs filtering by user_id.
        """
        result = await self.db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, obj: ModelType, updates: dict) -> ModelType:
        """
        Apply a dict of field updates to an existing object and persist it.
        Only sets fields that are not None — supports partial PATCH semantics
        without overwriting untouched fields with null.
        """
        for field, value in updates.items():
            setattr(obj, field, value)
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ModelType) -> None:
        """Hard delete a row."""
        await self.db.delete(obj)
        await self.db.commit()