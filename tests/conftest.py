import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# from redis import asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer


# --- POSTGRES CONTAINER (session-scoped: starts once, shared across all tests) ---
@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:15") as postgres:
        yield postgres


# --- REDIS CONTAINER (session-scoped) ---
@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:7") as redis:
        yield redis


@pytest.fixture(scope="session", autouse=True)
def set_test_env(postgres_container, redis_container):
    """Override env vars so your Config picks up test containers"""
    sync_url = postgres_container.get_connection_url()
    async_url = sync_url.replace(
        "postgresql+psycopg2://",  # testcontainers adds psycopg2 explicitly
        "postgresql+asyncpg://",
    )
    # Fallback in case it's a plain postgresql:// URL
    if async_url.startswith("postgresql://"):
        async_url = async_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    os.environ["DATABASE_URL"] = async_url
    os.environ["REDIS_URL"] = (
        f"redis://{redis_container.get_container_host_ip()}"
        f":{redis_container.get_exposed_port(6379)}"
    )
    # os.environ["ENVIRONMENT"] = "test"
    yield


# --- ASYNC ENGINE (session-scoped, built from container URL) ---
@pytest.fixture(scope="session")
async def async_engine(postgres_container, set_test_env):
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    user = postgres_container.username
    password = postgres_container.password
    db = postgres_container.dbname

    async_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
    engine = create_async_engine(async_url, echo=True, poolclass=NullPool)

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

    await engine.dispose()


# --- DB SESSION (function-scoped: fresh session per test) ---


@pytest.fixture(scope="function")
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with async_session() as session:
        yield session
        # Clean up committed data after each test
        await session.rollback()
        # Truncate all tables to reset state
        async with async_engine.begin() as conn:
            await conn.execute(
                text('TRUNCATE TABLE otp, profile, "user" RESTART IDENTITY CASCADE')
            )


@pytest.fixture(scope="session")
async def async_client(async_engine, set_test_env) -> AsyncGenerator[AsyncClient, None]:
    from src.db.database import get_session
    from src.limiter import limiter
    from src.main import app

    limiter.enabled = False

    # Override the get_session dependency so the APP uses the SAME engine as tests
    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async_session = async_sessionmaker(
            bind=async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client

    limiter.enabled = True  # restore after session
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def app_instance(async_engine, set_test_env):
    from src.db.database import get_session
    from src.main import app

    async def override_get_session():
        async_session = async_sessionmaker(
            bind=async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    return app  # ← expose the app object directly



# @pytest.fixture(autouse=True)
# async def setup_redis(app_instance):  # ← use app_instance, not async_client
#     redis_client = aioredis.from_url(
#         settings.REDIS_URL, encoding="utf-8", decode_responses=True
#     )
#     yield
#     await redis_client.flushdb()
#     await redis_client.aclose()


# --- REDIS CLIENT (function-scoped: flush after each test) ---
@pytest.fixture(scope="function")
def redis_client(redis_container):
    import redis

    client = redis.Redis(
        host=redis_container.get_container_host_ip(),
        port=redis_container.get_exposed_port(6379),
        decode_responses=True,
    )
    yield client
    client.flushall()  # wipe all data after each test

# Sample data 

    
@pytest.fixture
async def test_client():
    """
    Async HTTP test client for the FastAPI app.
 
    Uses ASGITransport to call the app directly without
    a real network connection — fast and deterministic.
 
    Mocks the PostgreSQL checkpointer and agent initialization.
    """
   
    from src.main import app
    from src.errors import register_global_error_handlers

    # Register error handlers BEFORE testing
    register_global_error_handlers(app)
    
    # Mock AsyncPostgresSaver.from_conn_string to return our mock
    with patch("src.main.init_db", new_callable=AsyncMock):
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            yield client