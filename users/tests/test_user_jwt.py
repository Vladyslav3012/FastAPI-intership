import pytest
from httpx import AsyncClient
from sqlalchemy import select
from users.models import RefreshTokenModel


@pytest.mark.asyncio
async def test_access_token(client: AsyncClient, db_session):

    sign_data = {
        "email": "access@test.com",
        "username": "access",
        "password": "password123",
        "check_password": "password123"
    }
    await client.post('/users/sign', json=sign_data)

    login_data = {
        "email": sign_data['email'],
        "password": sign_data['password']
    }
    login_response = await client.post("/users/login", data=login_data)
    assert login_response.status_code == 200

    tokens = login_response.json()
    access_token = tokens["access_token"]
    assert access_token is not None

    me_response = await client.get("/users/me",
                                   headers={"Authorization": f"Bearer {access_token}"})
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == sign_data["email"]
    assert me_data["username"] == sign_data["username"]



@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, db_session):

    sign_data = {
        "email": "refresh@test.com",
        "username": "refresher",
        "password": "password123",
        "check_password": "password123"
    }
    await client.post('/users/sign', json=sign_data)


    login_data = {
        "email": sign_data['email'],
        "password": sign_data['password']
    }
    login_response = await client.post("/users/login", data=login_data)
    assert login_response.status_code == 200

    query_old = select(RefreshTokenModel)
    res_old = await db_session.execute(query_old)
    token_in_db_before = res_old.scalars().one()
    old_jti = token_in_db_before.jti

    tokens = login_response.json()
    refresh_token = tokens['refresh_token']

    refresh_res = await client.post(
        "/users/refresh",
        headers={"Authorization": f"Bearer {refresh_token}"}
    )
    assert refresh_res.status_code == 200
    db_session.expire_all()

    new_tokens = refresh_res.json()
    new_refresh_token = new_tokens["refresh_token"]

    query_new = select(RefreshTokenModel)
    res_new = await db_session.execute(query_new)
    tokens_in_db = res_new.scalars().all()

    assert len(tokens_in_db) == 1
    assert tokens_in_db[0].jti != old_jti
    assert new_refresh_token != refresh_token

    reuse_res = await client.post(
        "/users/refresh",
        headers={"Authorization": f"Bearer {refresh_token}"}
    )
    assert reuse_res.status_code == 401


