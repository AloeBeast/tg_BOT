import asyncio
import json
import logging
from collections.abc import Callable
from typing import TypeVar

from services.redis_client import get_redis

AI_FALLBACK_MESSAGE = "Не удалось обработать запрос, попробуй позже"

logger = logging.getLogger(__name__)
T = TypeVar("T")


async def _run_with_retry(
    operation: Callable[[], T],
    *,
    operation_name: str,
    timeout_seconds: float,
    fallback: T,
    retries: int = 1,
) -> T:
    """Runs a blocking AI operation off the event loop with timeout and small retry budget."""
    attempts = retries + 1

    for attempt in range(1, attempts + 1):
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(operation),
                timeout=timeout_seconds,
            )
        except Exception:
            logger.exception(
                "%s failed on attempt %s/%s",
                operation_name,
                attempt,
                attempts,
            )
            if attempt < attempts:
                await asyncio.sleep(0.5 * attempt)

    return fallback


async def safe_chat_completion(
    operation: Callable[[], str],
    *,
    timeout_seconds: float,
    fallback: str = AI_FALLBACK_MESSAGE,
    retries: int = 1,
) -> str:
    """Safely executes a chat-completion call without blocking handlers."""
    return await _run_with_retry(
        operation,
        operation_name="AI chat completion",
        timeout_seconds=timeout_seconds,
        fallback=fallback,
        retries=retries,
    )


class UserRateLimiter:
    """Redis-backed per-user cooldown limiter."""

    def __init__(self, cooldown_seconds: float, prefix: str = "rl"):
        self.cooldown_seconds = int(cooldown_seconds)
        self.prefix = prefix

    async def is_allowed(self, user_id: int) -> bool:
        key = f"{self.prefix}:{user_id}"
        r = get_redis()
        current = await r.incr(key)
        if current == 1:
            await r.expire(key, self.cooldown_seconds)
        return current == 1


PROFILE_CACHE_TTL = 300


async def get_cached_profile(user_id: int) -> dict[str, str] | None:
    key = f"profile:{user_id}"
    r = get_redis()
    data = await r.get(key)
    if data:
        return json.loads(data)
    return None


async def set_cached_profile(user_id: int, profile: dict[str, str]) -> None:
    key = f"profile:{user_id}"
    r = get_redis()
    await r.set(key, json.dumps(profile), ex=PROFILE_CACHE_TTL)


async def invalidate_cached_profile(user_id: int) -> None:
    key = f"profile:{user_id}"
    r = get_redis()
    await r.delete(key)
