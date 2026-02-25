import logging
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (create_async_engine,
                                    async_sessionmaker, AsyncSession)
from typing import AsyncGenerator

from app.main import app
from app.config import settings
from app.config import Base, async_get_session
from app.redis_config import token_blacklist

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

TEST_DATABASE_URL = settings.test_database_url

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def prepare_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    app.dependency_overrides[async_get_session] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app),
                           base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True)
async def clear_redis():
    yield
    await token_blacklist.aclose()
