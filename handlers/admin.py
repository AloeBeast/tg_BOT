import logging

from aiogram import Router, types
from aiogram.filters import Command

from config import ADMIN_IDS
from database import get_stats

logger = logging.getLogger(__name__)
router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user is None or not _is_admin(message.from_user.id):
        return

    stats = await get_stats()
    text = (
        "📊 <b>Статистика</b>\n\n"
        f"👥 Всего пользователей: <b>{stats['total_users']}</b>\n"
        f"🟢 Активных сегодня: <b>{stats['today_users']}</b>\n"
        f"💬 Сообщений сегодня: <b>{stats['today_messages']}</b>\n\n"
        f"ℹ️ Статистика не сбрасывается при очистке истории пользователями."
    )
    await message.answer(text, parse_mode="HTML")
