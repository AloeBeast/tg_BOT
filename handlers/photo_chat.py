import logging

from aiogram import Router, Bot, F, types

from config import (
    AI_CHAT_TIMEOUT_SECONDS,
    AI_RETRY_COUNT,
    AI_VISION_TIMEOUT_SECONDS,
    HISTORY_LIMIT,
    MAX_IMAGE_BYTES,
    MIN_IMAGE_BYTES,
    PHOTO_RATE_LIMIT_SECONDS,
)
from database import save_message, get_history, get_user_profile
from services.ai_client import (
    AI_FALLBACK_MESSAGE,
    UserRateLimiter,
    safe_chat_completion,
    safe_vision_call,
)
from services.ai_text import get_ai_reply, build_system_prompt
from services.ai_vision import describe_image

logger = logging.getLogger(__name__)
router = Router()
_photo_rate_limiter = UserRateLimiter(PHOTO_RATE_LIMIT_SECONDS)


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

        # Шаг 1: получаем описание фото от vision-модели без блокировки event loop
        description = await safe_vision_call(
            lambda: describe_image(image_bytes),
            timeout_seconds=AI_VISION_TIMEOUT_SECONDS,
            retries=AI_RETRY_COUNT,
        )
        logger.debug("Vision description: %s", description)

        if description == AI_FALLBACK_MESSAGE:
            await message.answer(AI_FALLBACK_MESSAGE)
            return

        # Пользователь мог добавить подпись к фото — учитываем её
        caption = message.caption or ""

        user_note = f" Подпись пользователя к фото: {caption}" if caption else ""

        combined_message = f"[Пользователь прислал фото. Вот его описание: {description}]{user_note}"

        # Сохраняем в историю как обычное сообщение пользователя
        save_message(user_id, "user", combined_message)

        # Шаг 2: основная модель (Виктор) комментирует фото в своём стиле
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
        logger.exception("Photo handler failed")
        await message.answer(AI_FALLBACK_MESSAGE)
