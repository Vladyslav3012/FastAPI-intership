from datetime import timedelta

from .config import settings
import datetime
import redis.asyncio as redis

# settings for jwt blacklist
token_blacklist = redis.from_url(f"{settings.REDIS_URL}/0")


async def add_jti_to_blocklist(jti: str, exp: int) -> None:
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    ttl = int(exp - now)

    if ttl <= 0:
        return
    await token_blacklist.set(name=jti, value='', ex=ttl)


async def check_token_in_blacklist(jti: str) -> bool:
    res = await token_blacklist.get(jti)
    return res is not None


# settings for crypto cache
crypto_list = redis.from_url(f"{settings.REDIS_URL}/1")


async def add_price_to_list(coin_name: str, price: float) -> None:
    await crypto_list.set(name=coin_name, value=price, ex=10)


async def check_coin_in_list(coin_name: str) -> float | None:
    res = await crypto_list.get(coin_name)
    if res is not None:
        return float(res)
    return None