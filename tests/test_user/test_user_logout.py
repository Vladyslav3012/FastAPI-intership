import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.users.models import RefreshTokenModel


@pytest.mark.asyncio
async def test_logout_user(client: AsyncClient, db_session):
    sign_data = {
        "email": "test@example.com",
        "username": "testuser",
        "age": 25,
        "password": "password123",
        "check_password": "password123"
    }

    response = await client.post("/users/sign", json=sign_data)
    assert response.status_code == 200

    login_data = {
        "email": sign_data['email'],
        "password": sign_data['password']
    }
    login_response = await client.post("/users/login", data=login_data)
    assert login_response.status_code == 200

    tokens = login_response.json()
    access_token = tokens["access_token"]

    logout_response = await client.post('/users/logout',
                                        headers={"Authorization": f"Bearer {access_token}"})
    assert logout_response.status_code == 200

    me_response = await client.get("/users/me",
                                   headers={"Authorization": f"Bearer {access_token}"})
    assert me_response.status_code == 401

