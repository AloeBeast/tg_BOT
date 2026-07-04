import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from config import BOT_TOKEN
from database import close_pool, init_db, init_pool
from handlers.menu import router as menu_router
from handlers.text_chat import router as text_chat_router
from handlers.photo_chat import router as photo_chat_router
from handlers.admin import router as admin_router
from services.redis_client import close_redis, init_redis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)  # type: ignore[arg-type]
dp = Dispatcher()

dp.include_router(menu_router)        # меню и кнопки — раньше всех
dp.include_router(admin_router)       # админ-команды
dp.include_router(photo_chat_router)  # фото-хендлер должен быть выше текстового
dp.include_router(text_chat_router)


async def main():
    await init_pool()
    await init_redis()
    try:
        logger.info("Initializing database")
        await init_db()

        await bot.set_my_commands([
            BotCommand(command="menu", description="📋 Главное меню"),
            BotCommand(command="subscription", description="💎 Подписка"),
            BotCommand(command="memory", description="🧠 Память бота"),
        ])

        logger.info("Starting bot polling")
        await dp.start_polling(bot)  # type: ignore
    finally:
        logger.info("Closing connections")
        await close_redis()
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
