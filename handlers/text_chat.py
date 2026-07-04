import asyncio
import logging

from aiogram import Router, Bot, types
from aiogram.filters import Command

from config import AI_CHAT_TIMEOUT_SECONDS, AI_RETRY_COUNT, HISTORY_LIMIT, TEXT_RATE_LIMIT_SECONDS
from database import (
    save_message,
    get_history,
    get_user_profile,
    update_user_name,
    append_user_fact,
    track_user_activity,
)
from services.ai_client import (
    AI_FALLBACK_MESSAGE,
    UserRateLimiter,
    get_cached_profile,
    invalidate_cached_profile,
    safe_chat_completion,
    set_cached_profile,
)
from services.ai_text import get_ai_reply, extract_profile_update, build_system_prompt
from services.animation import animate_thinking

logger = logging.getLogger(__name__)
router = Router()
_text_rate_limiter = UserRateLimiter(TEXT_RATE_LIMIT_SECONDS, prefix="rl:text")


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

        if not await _text_rate_limiter.is_allowed(user_id):
            await message.answer("Подожди секунду, не торопись.")
            return

        thinking_msg = await message.answer("⏳ Виктор думает  ")
        stop_event = asyncio.Event()
        anim_task = asyncio.create_task(
            animate_thinking(bot, message.chat.id, thinking_msg.message_id, stop_event)
        )

        try:
            profile_invalidated = False

            try:
                update = await asyncio.wait_for(
                    asyncio.to_thread(extract_profile_update, user_text),
                    timeout=AI_CHAT_TIMEOUT_SECONDS,
                )
            except Exception:
                logger.exception("Profile extraction failed")
                update = {"name": "", "fact": ""}

            if update["name"]:
                await update_user_name(user_id, update["name"])
                profile_invalidated = True

            if update["fact"]:
                await append_user_fact(user_id, update["fact"])
                profile_invalidated = True

            await save_message(user_id, "user", user_text)
            await track_user_activity(user_id)

            if profile_invalidated:
                await invalidate_cached_profile(user_id)
                profile = await get_user_profile(user_id)
                await set_cached_profile(user_id, profile)
            else:
                profile = await get_cached_profile(user_id)
                if profile is None:
                    profile = await get_user_profile(user_id)
                    await set_cached_profile(user_id, profile)

            system_prompt = build_system_prompt(profile)
            history = await get_history(user_id, limit=HISTORY_LIMIT)

            messages = [{"role": "system", "content": system_prompt}] + history

            ai_answer = await safe_chat_completion(
                lambda: get_ai_reply(messages),
                timeout_seconds=AI_CHAT_TIMEOUT_SECONDS,
                retries=AI_RETRY_COUNT,
            )

            await save_message(user_id, "assistant", ai_answer)

        finally:
            stop_event.set()
            await anim_task

        await thinking_msg.edit_text(ai_answer)

    except Exception:
        logger.exception("Text handler crashed")
        await message.answer(AI_FALLBACK_MESSAGE)
