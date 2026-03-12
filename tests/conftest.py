import logging
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (create_async_engine,
                                    async_sessionmaker, AsyncSession)
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch
from fastapi import Request, Response
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


async def mock_rate_limiter_call(self, request: Request, response: Response):
    return None

@pytest_asyncio.fixture(autouse=True)
def disable_rate_limiting():
    with patch('fastapi_limiter.depends.RateLimiter.__call__', new=mock_rate_limiter_call):
        yield



@pytest_asyncio.fixture(scope="function")
@patch('app.users.views.view_auth.sending_email_message.delay')
@patch('app.users.utils.auth_utils.check_token_in_blacklist', new_callable=AsyncMock)
async def authorized_client(mock_redis_check, mock_email,
                                client: AsyncClient):

    mock_redis_check.return_value = False

    sign_data = {
    "email": "test@test.com",
    "username": "test",
    "password": "password123",
    "check_password": "password123"
    }
    await client.post('/users/auth/sign', json=sign_data)

    login_data = {
         "email": sign_data['email'],
         "password": sign_data['password']
    }
    login_response = await client.post("/users/auth/login", json=login_data)
    assert login_response.status_code == 200

    tokens = login_response.json()
    access_token = tokens["access_token"]
    assert access_token is not None
    client.headers.update({"Authorization": f"Bearer {access_token}"})
    return client
