from unittest.mock import patch, AsyncMock

import pytest
from httpx import AsyncClient

from app.config import login_request_limit
from app.main import app

async def override_rate_limit():
    pass

app.dependency_overrides[login_request_limit] = override_rate_limit

@pytest.mark.asyncio
@patch('app.users.views.view_auth.sending_email_message.delay')
@patch('app.users.views.view_auth.check_token_in_blacklist', new_callable=AsyncMock)
@patch('app.users.views.view_auth.add_jti_to_blocklist', new_callable=AsyncMock)
@patch('app.users.utils.auth_utils.check_token_in_blacklist', new_callable=AsyncMock)
async def test_logout_user(mock_redis_utils, mock_redis_add,
                           mock_redis_check, mock_email,
                           client: AsyncClient, db_session):

    mock_redis_add.return_value = False
    mock_redis_check.return_value = False
    sign_data = {
        "email": "test@example.com",
        "username": "testuser",
        "age": 25,
        "password": "password123",
        "check_password": "password123"
    }

    response = await client.post("/users/auth/sign", json=sign_data)
    assert response.status_code == 200

    login_data = {
        "email": sign_data['email'],
        "password": sign_data['password']
    }
    login_response = await client.post("/users/auth/login", json=login_data)
    assert login_response.status_code == 200

    tokens = login_response.json()
    access_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    logout_response = await client.post('/users/auth/logout',
                                        headers=headers)
    assert logout_response.status_code == 200

    me_response = await client.get("/users/auth/me",
                                   headers=headers)
    assert me_response.status_code == 401
