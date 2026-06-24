"""
GET    /competitors          — list all competitors for current user
POST   /competitors          — add competitor, triggers sub-URL discovery
GET    /competitors/{id}     — get one competitor with its sources
PATCH  /competitors/{id}     — update name or URL
DELETE /competitors/{id}     — remove competitor and its sources
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_session
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.competitors.dependencies import get_competitor_repository, valid_competitor_id
from src.competitors.models import Competitor
from src.competitors.repository import CompetitorRepository, CompetitorSourceRepository
from src.competitors.schemas import (
    CompetitorCreate,
    CompetitorRead,
    CompetitorSummary,
    CompetitorUpdate,
)
from src.competitors.service import CompetitorService
from src.db.database import init_db

router = APIRouter()

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(init_db)]
ValidCompetitor = Annotated[Competitor, Depends(valid_competitor_id)]


def get_competitor_service(
    session: AsyncSession = Depends(get_session),
) -> CompetitorService:
    """Wires up CompetitorService with both repositories for the current session."""
    return CompetitorService(
        competitor_repo=CompetitorRepository(session),
        source_repo=CompetitorSourceRepository(session),
    )
 
@router.get("", response_model=list[CompetitorSummary])
async def list_competitors(
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[CompetitorRepository, Depends(get_competitor_repository)],
) -> list[Competitor]:
    """
    Returns all competitors belonging to the authenticated user.
    """
    return await repo.get_all_by_user(current_user.id)

@router.post("", response_model=CompetitorRead, status_code=status.HTTP_201_CREATED)
async def add_competitor(
    body: CompetitorCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CompetitorService, Depends(get_competitor_service)],
) -> Competitor:
    """
    Adds a new competitor and immediately runs sub-URL discovery so
    the competitor has sources ready for its first research run.
 
    Raises CompetitorAlreadyExists (422) if the name already exists
    for this user.
    """
    return await service.add_competitor(
        user_id=current_user.id,
        name=body.name,
        main_url=body.main_url,
    )


@router.get("/{competitor_id}", response_model=CompetitorRead)
async def get_competitor(
    competitor: Annotated[Competitor, Depends(valid_competitor_id)],
):
    """
    Returns one competitor with its full list of discovered sources.
    valid_competitor_id() handles existence + ownership — if either
    check fails this never runs and the caller gets a 404.
    """
    return competitor


@router.patch("/{competitor_id}", response_model=CompetitorRead)
async def update_competitor(
    competitor: Annotated[Competitor, Depends(valid_competitor_id)],
    updates: CompetitorUpdate,
    service: CompetitorService = Depends(),
):
    """
    Partial update — only fields included in the request body are changed.
    Changing main_url does NOT re-trigger sub-URL discovery (post-MVP).
    """
    return await service.update_competitor(competitor, updates.model_dump(exclude_unset=True))


@router.delete("/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_competitor(
    competitor: Annotated[Competitor, Depends(valid_competitor_id)],
    service: CompetitorService = Depends(),
):
    """
    Deletes the competitor. Cascade on the relationship handles
    sources, reports, alerts, and jobs automatically — no manual
    child deletion needed here.
    """
    await service.delete_competitor(competitor)