import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
@patch("app.parsing.views.check_coin_in_list", new_callable=AsyncMock)
@patch("app.parsing.views.add_price_to_list", new_callable=AsyncMock)
async def test_get_current_price_parsing(redis_add: AsyncMock, redis_check: AsyncMock,
                                         client: AsyncClient):
     redis_check.return_value = None
     responce = await client.get('/parsing/crypto/current_price/bitcoin')
     assert responce.status_code == 200

     data = responce.json()
     assert data["coin"] == "bitcoin"
     assert isinstance(data["price"], float)
     assert "$" in data["display_price"]
     assert isinstance(data["display_price"], str)
     
     redis_check.assert_called_once()
     redis_add.assert_called_once()


@pytest.mark.asyncio
async def test_get_current_price_with_wrong_coin_name(client: AsyncClient):

     responce = await client.get('/parsing/crypto/current_price/wrong_name')

     assert responce.status_code == 422
