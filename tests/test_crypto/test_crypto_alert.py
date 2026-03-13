import pytest
from httpx import AsyncClient
from app.parsing.utils import EnumNameCoin
from app.crypto.models import CoinModel


@pytest.mark.asyncio
async def test_add_crypto_alert(authorized_client: AsyncClient, db_session):

    coin_name = EnumNameCoin.btc.value
    new_coin = CoinModel(name=coin_name, current_price=123.123)
    db_session.add(new_coin)
    await db_session.commit()

    alert_body = {
         "coin_name": coin_name,
         "target_price": 1,
         "conditions": "above"
         }

    alert_response = await authorized_client.post("/alert/", json=alert_body)
    assert alert_response.status_code == 200

    response_data = alert_response.json()
    assert "id" in response_data
    assert response_data["is_active"] is True
    assert response_data["target_price"] == alert_body["target_price"]
    assert response_data["coin"]["name"] == alert_body["coin_name"]
    assert response_data["conditions"] == alert_body["conditions"]
    assert response_data["coin"]['current_price'] == new_coin.current_price

    get_alert_response = await authorized_client.get("/alert/")
    assert get_alert_response.status_code == 200

    get_alert_body = get_alert_response.json()
    assert len(get_alert_body) == 1


@pytest.mark.asyncio
async def test_add_ctypto_alert_with_wrong_data(authorized_client: AsyncClient, db_session):

    alert_body = {
         "coin_name": "fake_token",
         "target_price": 1,
         "conditions": "above"
     }

    alert_response = await authorized_client.post("/alert/", json=alert_body)
    assert alert_response.status_code == 404

    response_data = alert_response.json()
    assert "id" not in response_data
    assert "not found" in response_data['detail']

    get_alert_response = await authorized_client.get("/alert/")
    assert get_alert_response.status_code == 200

    get_alert_body = get_alert_response.json()
    assert len(get_alert_body) == 0


@pytest.mark.asyncio
async def test_add_crypto_alert_unauthorized(client: AsyncClient):
    alert_body = {
         "coin_name": "bitcoin",
         "target_price": 1,
         "conditions": "above"
         }

    alert_response = await client.post("/alert/", json=alert_body)
    assert alert_response.status_code == 401

    response_data = alert_response.json()
    assert "id" not in response_data

    get_alert_response = await client.get("/alert/")
    assert get_alert_response.status_code == 401
