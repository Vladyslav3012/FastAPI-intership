import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_get_current_price_parsing(client: AsyncClient):

     responce = await client.get('/parsing/crypto/current_price/bitcoin')
     assert responce.status_code == 200

     data = responce.json()
     assert data["coin"] == "bitcoin"
     assert isinstance(data["price"], float)
     assert "$" in data["display_price"]
     assert isinstance(data["display_price"], str)


@pytest.mark.asyncio
async def test_get_current_price_with_wrong_coin_name(client: AsyncClient):

     responce = await client.get('/parsing/crypto/current_price/wrong_name')

     assert responce.status_code == 422
