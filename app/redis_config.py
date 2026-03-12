import logging
from .config import settings
import datetime
import redis.asyncio as redis


logger = logging.getLogger(__name__)

# settings for jwt blacklist
token_blacklist = redis.from_url(f"{settings.REDIS_URL}/0")


async def add_jti_to_blocklist(jti: str, exp: int) -> None:
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    ttl = int(exp - now)
    logger.info(f"Try add token in blacklist. Args: {jti=}, {ttl=}")
    if ttl <= 0:
        logger.info(f"Token has been expired, cancel add to blacklist")
        return
    await token_blacklist.set(name=jti, value='', ex=ttl)
    logger.info(f"Succes add token with {jti=} to blacklist. TTL: {ttl}")

async def check_token_in_blacklist(jti: str) -> bool:
    logger.info(f'Try get token with {jti=}')
    res = await token_blacklist.get(jti)
    if res is not None:
        logger.warning(f"Token with {jti=} in blacklist")
        return True
    logger.info(f"Token with {jti=} not in blacklist")
    return False


# settings for crypto cache
crypto_list = redis.from_url(f"{settings.REDIS_URL}/1")


async def add_price_to_list(coin_name: str, price: float) -> None:
    logger.info(f"Start set new coin new to cache, {coin_name} = {price}")
    await crypto_list.set(name=coin_name, value=price, ex=10)
    logger.info("Success caching")


async def check_coin_in_list(coin_name: str) -> float | None:
    logger.info(f"Try get {coin_name=} from cache")
    res = await crypto_list.get(coin_name)
    if res is not None:
        logger.info(f"Succes get {coin_name=} from cache, value: {res}")
        return float(res)
    logger.info(f"Coin with {coin_name=} not found in cache")
    return None