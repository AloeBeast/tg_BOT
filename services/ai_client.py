import asyncio
import logging
import time
from collections.abc import Callable
from typing import TypeVar

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
    """Simple in-memory per-user cooldown limiter."""

    def __init__(self, cooldown_seconds: float):
        self.cooldown_seconds = cooldown_seconds
        self._last_seen: dict[int, float] = {}

    def is_allowed(self, user_id: int) -> bool:
        now = time.monotonic()
        last_seen = self._last_seen.get(user_id)
        if last_seen is not None and now - last_seen < self.cooldown_seconds:
            return False

        self._last_seen[user_id] = now
        return True
