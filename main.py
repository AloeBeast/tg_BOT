import asyncio

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from database import init_db
from handlers.text_chat import router as text_chat_router
from handlers.photo_chat import router as photo_chat_router

bot = Bot(token=BOT_TOKEN)  # type: ignore[arg-type]
dp = Dispatcher()

dp.include_router(photo_chat_router)  # фото-хендлер должен быть выше текстового
dp.include_router(text_chat_router)


async def main():
    init_db()
    await dp.start_polling(bot) # type: ignore


if __name__ == "__main__":
    asyncio.run(main())