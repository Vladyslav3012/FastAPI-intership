import pytest
from httpx import AsyncClient
from sqlalchemy import select
from users.models import UsersModel, UserRoleEnum


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, db_session):
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "age": 25,
        "password": "password123",
        "check_password": "password123"
    }

    response = await client.post("/users/sign", json=user_data)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "password" not in data

    query = select(UsersModel).where(UsersModel.email == user_data.get('email'))
    result = await db_session.execute(query)
    user_in_db = result.scalars().one_or_none()

    assert user_in_db is not None
    assert user_in_db.id == 1
    assert user_in_db._hashed_password_ != user_data.get('password')
    assert user_in_db.active == True
    assert user_in_db.role == UserRoleEnum.regular


@pytest.mark.asyncio
async def test_password_not_match_register(client: AsyncClient, db_session):
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "age": 25,
        "password": "password123",
        "check_password": "password"
    }

    response = await client.post("/users/sign", json=user_data)

    assert response.status_code == 422
    data = response.json()
    assert "Passwords do not match" in str(data)
    query = select(UsersModel).where(UsersModel.email == user_data.get('email'))
    result = await db_session.execute(query)
    user_in_db = result.scalars().one_or_none()

    assert user_in_db is None

@pytest.mark.asyncio
async def test_email_has_been_used(client: AsyncClient, db_session):
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "age": 25,
        "password": "password123",
        "check_password": "password123"
    }

    response = await client.post("/users/sign", json=user_data)
    assert response.status_code == 200

    second_response = await client.post("/users/sign", json=user_data)
    assert second_response.status_code == 409
    data = second_response.json()
    assert "This email has been used" in str(data)

    query = select(UsersModel).where(UsersModel.email == user_data.get('email'))
    result = await db_session.execute(query)
    user_in_db = result.scalars().one_or_none()

    assert user_in_db is not None

