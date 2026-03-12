import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient



@pytest.mark.asyncio
async def test_start_parsing_web(client: AsyncClient):
     url = 'https://www.currentaffairs.org/news/downton-abbey-and-the-myth-of-the-good-aristocrat'

     response = await client.get("/parsing/web", params={'url': url})
     assert response.status_code == 200

     data = response.json()
     assert "task_id" in data
     assert data["task_ready"] is False
     assert data["task_status"] == "PENDING" or data["task_status"] == "STARTED"
     


@pytest.mark.asyncio
async def test_start_parsing_web_with_wrong_url(client: AsyncClient):     
     url = '/news/downton-abbey-and-the-myth-of-the-good-aristocrat'

     response = await client.get("/parsing/web", params={'url': url})
     assert response.status_code == 422

     data = response.json()
     assert "task_id" not in data
     


@pytest.mark.asyncio
async def test_check_status_parsing_web(client: AsyncClient):
     url_for_parsing = 'https://www.currentaffairs.org/news/downton-abbey-and-the-myth-of-the-good-aristocrat'

     response_start_parsing = await client.get("parsing/web", params={'url': url_for_parsing})
     assert response_start_parsing.status_code == 200
     data = response_start_parsing.json()
     task_id = data["task_id"]

     url_check = f"/parsing/web/status/{task_id}"
     response_check_status = await client.get(url_check)
     assert response_check_status.status_code == 200