import asyncio
import base64
import logging

from aiogram import Router, Bot, F, types

from config import (
    AI_CHAT_TIMEOUT_SECONDS,
    AI_RETRY_COUNT,
    HISTORY_LIMIT,
    MAX_IMAGE_BYTES,
    MIN_IMAGE_BYTES,
    PHOTO_RATE_LIMIT_SECONDS,
)
from database import (
    append_user_fact,
    get_history,
    get_user_profile,
    save_message,
    update_user_name,
)
from services.ai_client import (
    AI_FALLBACK_MESSAGE,
    UserRateLimiter,
    safe_chat_completion,
)
from services.ai_text import (
    build_system_prompt,
    extract_profile_update,
    get_ai_reply,
)

logger = logging.getLogger(__name__)
router = Router()
_photo_rate_limiter = UserRateLimiter(PHOTO_RATE_LIMIT_SECONDS)


def _build_image_message(image_bytes: bytes, caption: str) -> list[dict[str, object]]:
    """Builds a multimodal OpenAI-compatible message content payload."""
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    user_text = caption.strip() or "Ответь на сообщение пользователя, учитывая изображение."

    return [
        {
            "type": "text",
            "text": user_text,
        },
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}",
            },
        },
    ]


@router.message(F.photo)
async def handle_photo(message: types.Message, bot: Bot):
    try:
        if message.from_user is None:
            return

        if not message.photo:
            await message.answer("Не смог скачать фото, попробуй ещё раз.")
            return

        user_id = message.from_user.id

        if not _photo_rate_limiter.is_allowed(user_id):
            await message.answer("Слишком часто отправляешь фото, подожди немного")
            return

        await bot.send_chat_action(message.chat.id, "typing")

        # Берём фото в максимальном доступном качестве (последнее в списке размеров)
        photo = message.photo[-1]
        if photo.file_size and photo.file_size > MAX_IMAGE_BYTES:
            await message.answer("Фото слишком большое, отправь изображение поменьше")
            return

        file = await bot.get_file(photo.file_id)

        if file.file_path is None:
            await message.answer("Не смог скачать фото, попробуй ещё раз.")
            return

        file_bytes_io = await bot.download_file(file.file_path)

        if file_bytes_io is None:
            await message.answer("Не смог скачать фото, попробуй ещё раз.")
            return

        image_bytes = file_bytes_io.read()
        if len(image_bytes) < MIN_IMAGE_BYTES:
            await message.answer("Не удалось обработать изображение, попробуй другое фото")
            return
        if len(image_bytes) > MAX_IMAGE_BYTES:
            await message.answer("Фото слишком большое, отправь изображение поменьше")
            return

        caption = message.caption or ""
        if caption.strip():
            try:
                update = await asyncio.wait_for(
                    asyncio.to_thread(extract_profile_update, caption),
                    timeout=AI_CHAT_TIMEOUT_SECONDS,
                )
            except Exception:
                logger.exception("Profile extraction for photo caption failed")
                update = {"name": "", "fact": ""}

            if update["name"]:
                update_user_name(user_id, update["name"])
            if update["fact"]:
                append_user_fact(user_id, update["fact"])

        profile = get_user_profile(user_id)
        system_prompt = build_system_prompt(profile)
        history = get_history(user_id, limit=HISTORY_LIMIT)

        messages = [{"role": "system", "content": system_prompt}] + history
        messages.append({"role": "user", "content": _build_image_message(image_bytes, caption)})

        ai_answer = await safe_chat_completion(
            lambda: get_ai_reply(messages),
            timeout_seconds=AI_CHAT_TIMEOUT_SECONDS,
            retries=AI_RETRY_COUNT,
        )

        saved_text = caption.strip() or "[Пользователь прислал фото без подписи]"
        save_message(user_id, "user", f"[Фото] {saved_text}")
        save_message(user_id, "assistant", ai_answer)

        await message.answer(ai_answer)
    except Exception:
        logger.exception("Photo handler failed")
        await message.answer(AI_FALLBACK_MESSAGE)
