from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import settings
from src.custom_logging import get_logger

log = get_logger(__name__)

# Ensure DATABASE_URL is set before creating the engine
if settings.DATABASE_URL is None:
    raise ValueError(
        "DATABASE_URL must be set in environment or assembled from POSTGRES_* variables"
    )

async_engine = create_async_engine(url=settings.DATABASE_URL, echo=True)

async def init_db():
    """
    Called on startup.

    Table creation and schema migrations are handled by Alembic
    (`alembic upgrade head` runs in the startup script before the server starts).
    This function is kept as a hook for any future startup DB logic
    (e.g. seeding default data).
    """
    log.info("db.ready")
 
    
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
