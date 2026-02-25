import logging
from curl_cffi.requests import AsyncSession
from fastapi import APIRouter, HTTPException
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from app.crypto.utils import EnumNameCoin, parsing_url, formated_to_display_price
from app.redis_config import add_price_to_list, check_coin_in_list


router = APIRouter(tags=['Parsing'], prefix='/crypto/parsing')
logger = logging.getLogger(__name__)
user_agent = UserAgent().random


@router.get("/current_price/{coin_name}")
async def get_current_token_price(coin_name: EnumNameCoin):
    coin_name_value = coin_name.value

    # check price in cache
    price_from_cache = await check_coin_in_list(coin_name_value)
    if price_from_cache:
        display_price = formated_to_display_price(price_from_cache)
        return {
            "coin": coin_name_value,
            "price": price_from_cache,
            "display_price": display_price
        }

    # if price not found start parsing
    url = f"{parsing_url}/{coin_name_value}"
    headers = {"user-agent": user_agent}

    async with AsyncSession(impersonate='chrome120') as client:
        response = await client.get(url, headers=headers)

        if response.status_code != 200:
            logger.error(f"Parsing return {response.status_code}")
            raise HTTPException(status_code=400, detail=f"Failed to fetch data, status: {response.status_code}")

        html_text = response.text

    soup = BeautifulSoup(html_text, 'lxml')
    price_tag = soup.select_one('span[data-price-usd]')
    logger.info(f"Price tag {price_tag}")

    if price_tag:
        raw_value = price_tag.get('data-price-usd')
        logger.info(f"Raw value {raw_value}")

        clean_price = float(raw_value)

        display_price = formated_to_display_price(clean_price)

        # add price to cache
        await add_price_to_list(coin_name_value, clean_price)

        return {
            "coin": coin_name_value,
            "price": clean_price,
            "display_price": display_price
        }
    return {"Error": "Tag not found "}

