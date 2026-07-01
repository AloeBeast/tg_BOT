import asyncio
import logging

from aiogram import Router, Bot, types
from aiogram.filters import CommandStart

from config import AI_CHAT_TIMEOUT_SECONDS, AI_RETRY_COUNT, HISTORY_LIMIT
from database import save_message, get_history, get_user_profile, update_user_name, append_user_fact
from services.ai_client import AI_FALLBACK_MESSAGE, safe_chat_completion
from services.ai_text import get_ai_reply, extract_profile_update, build_system_prompt

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("О, ещё один. Ладно, погнали, спрашивай что хотел — я Виктор, отвечу быстро и по делу, но без соплей.")


@router.message()
async def handle_message(message: types.Message, bot: Bot):
    try:
        user_text = message.text or ""

        if not user_text:
            await message.answer("Пришли, пожалуйста, текстовое сообщение.")
            return

        if message.from_user is None:
            return

        user_id = message.from_user.id

        await bot.send_chat_action(message.chat.id, "typing")

        try:
            update = await asyncio.wait_for(
                asyncio.to_thread(extract_profile_update, user_text),
                timeout=AI_CHAT_TIMEOUT_SECONDS,
            )
        except Exception:
            logger.exception("Profile extraction wrapper failed")
            update = {"name": "", "fact": ""}

        if update["name"]:
            update_user_name(user_id, update["name"])
        if update["fact"]:
            append_user_fact(user_id, update["fact"])

        save_message(user_id, "user", user_text)

        profile = get_user_profile(user_id)
        system_prompt = build_system_prompt(profile)
        history = get_history(user_id, limit=HISTORY_LIMIT)

        messages = [{"role": "system", "content": system_prompt}] + history

        ai_answer = await safe_chat_completion(
            lambda: get_ai_reply(messages),
            timeout_seconds=AI_CHAT_TIMEOUT_SECONDS,
            retries=AI_RETRY_COUNT,
        )

        save_message(user_id, "assistant", ai_answer)

        await message.answer(ai_answer)
    except Exception:
        logger.exception("Text handler failed")
        await message.answer(AI_FALLBACK_MESSAGE)
