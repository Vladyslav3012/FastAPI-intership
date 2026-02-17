from .config import settings
import datetime
import redis.asyncio as redis


token_blacklist = redis.StrictRedis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    decode_responses=True
)

async def add_jti_to_blocklist(jti: str, exp: int) -> None:
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    ttl = int(exp - now)

    if ttl <= 0:
        return
    await token_blacklist.set(name=jti, value='', ex=ttl)


async def check_token_in_blacklist(jti: str) -> bool:
    res = await token_blacklist.get(jti)
    return res is not None