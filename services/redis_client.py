import logging

import redis.asyncio as redis

from config import REDIS_URL

logger = logging.getLogger(__name__)
_pool: redis.ConnectionPool | None = None


async def init_redis() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool.from_url(
            REDIS_URL,
            max_connections=20,
            decode_responses=True,
            socket_timeout=10,
            socket_connect_timeout=10,
            health_check_interval=30,
        )
        logger.info("Redis pool created")
    return redis.Redis(connection_pool=_pool)


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.disconnect()
        _pool = None
        logger.info("Redis pool closed")


def get_redis() -> redis.Redis:
    if _pool is None:
        raise RuntimeError("Redis pool not initialized; call init_redis() at startup")
    return redis.Redis(connection_pool=_pool)
