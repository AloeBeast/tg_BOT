import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)

_FRAMES = [
    "⏳ Виктор думает  ",
    "⏳ Виктор думает .",
    "⏳ Виктор думает . .",
    "⏳ Виктор думает . . .",
]


async def animate_thinking(
    bot: Bot,
    chat_id: int,
    message_id: int,
    stop_event: asyncio.Event,
    interval: float = 0.2,
) -> None:
    """Анимирует 'Виктор думает...' в сообщении, обновляя точки и статус typing."""
    frame = 0
    while not stop_event.is_set():
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=_FRAMES[frame % len(_FRAMES)],
            )
        except TelegramBadRequest:
            pass
        except Exception:
            logger.debug("Animation edit skipped", exc_info=True)
        frame += 1

        await bot.send_chat_action(chat_id, "typing")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass
