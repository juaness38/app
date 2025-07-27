import redis.asyncio as aioredis
import os
from dotenv import load_dotenv

load_dotenv()

_redis_client = None

async def get_redis_client():
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            os.getenv("REDIS_URL"),
            decode_responses=True
        )
    return _redis_client