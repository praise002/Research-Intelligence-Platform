"""
Competitor dependencies — injected into competitor route handlers.

valid_competitor_id() is the single guard used by every route that
operates on a specific competitor:
    GET    /competitors/{competitor_id}
    PATCH  /competitors/{competitor_id}
    DELETE /competitors/{competitor_id}

It handles three checks in one place so the router stays clean:
    1. Does the competitor exist?
    2. Does it belong to the current user?
    3. If either fails → 404 (never 403 — see security note below)

Security note: we return 404 for both "not found" and "found but belongs
to another user" — returning 403 would confirm the resource exists,
leaking competitor IDs across user accounts (resource enumeration attack).
"""

import uuid

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import get_current_user
from src.competitors.exceptions import CompetitorNotFound
from src.competitors.models import Competitor
from src.competitors.repository import CompetitorRepository
from src.db.database import get_session
from src.db.models import User


def get_competitor_repository(
    session: AsyncSession = Depends(get_session),
) -> CompetitorRepository:
    """Provides a CompetitorRepository bound to the current request's DB session."""
    return CompetitorRepository(session)


async def valid_competitor_id(
    competitor_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    repo: CompetitorRepository = Depends(get_competitor_repository),
) -> Competitor:
    """
    Resolves a competitor by ID and confirms ownership.

    FastAPI extracts competitor_id directly from the path parameter —
    no manual UUID parsing needed in the router.

    USAGE (in router.py):
        from typing import Annotated
        from fastapi import Depends
        from src.competitors.dependencies import valid_competitor_id

        @router.get("/{competitor_id}", response_model=CompetitorRead)
        async def get_competitor(
            competitor: Annotated[Competitor, Depends(valid_competitor_id)],
        ):
            return competitor
    """
    competitor = await repo.get_by_id(competitor_id)

    if not competitor or competitor.user_id != current_user.id:
        raise CompetitorNotFound()

    return competitor