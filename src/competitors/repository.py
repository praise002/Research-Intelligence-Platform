import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.competitors.models import Competitor, CompetitorSource
from src.repositories.base_repository import BaseRepository


class CompetitorRepository(BaseRepository[Competitor]):
    """CRUD for competitors, scoped to the owning user."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Competitor)

    async def get_all_by_user(self, user_id: uuid.UUID) -> list[Competitor]:
        """
        Used by GET /competitors and by scheduler_task.py (Phase 10.4)
        when fanning out parallel research jobs — one Celery task per
        competitor returned here.
        """
        result = await self.db.execute(
            select(Competitor).where(Competitor.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_by_name_and_user(self, user_id: uuid.UUID, name: str) -> Competitor | None:
        """
        Used by service.add_competitor() to enforce COMP_002
        (CompetitorAlreadyExists) before inserting a duplicate.
        """
        result = await self.db.execute(
            select(Competitor).where(
                Competitor.user_id == user_id,
                Competitor.name == name,
            )
        )
        return result.scalar_one_or_none()


class CompetitorSourceRepository(BaseRepository[CompetitorSource]):
    """CRUD for the individual pages discovered per competitor."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, CompetitorSource)

    async def get_sources_by_competitor(self, competitor_id: uuid.UUID) -> list[CompetitorSource]:
        """Used to populate CompetitorResponse.sources and by data_fetcher.py (Phase 8.3)."""
        result = await self.db.execute(
            select(CompetitorSource).where(CompetitorSource.competitor_id == competitor_id)
        )
        return list(result.scalars().all())

    async def bulk_create(self, sources: list[CompetitorSource]) -> list[CompetitorSource]:
        """
        Used by service.save_discovered_sources() — sub-URL discovery
        typically returns 4-10 URLs at once, so insert them in a single
        transaction rather than one commit per URL.
        """
        self.db.add_all(sources)
        await self.db.commit()
        for source in sources:
            await self.db.refresh(source)
        return sources

    # async def delete_by_competitor(self, competitor_id: uuid.UUID) -> None:
    #     """
    #     Used when DELETE /competitors/{id} cascades to its sources —
    #     SQLModel/SQLAlchemy doesn't cascade-delete by default without
    #     explicit relationship config, so this is done manually here.
    #     """
    #     sources = await self.get_sources_by_competitor(competitor_id)
    #     for source in sources:
    #         await self.db.delete(source)
    #     await self.db.commit()