import logging

from aiogram import Router, Bot, F, types

from config import HISTORY_LIMIT
from database import save_message, get_history, get_user_profile
from services.ai_text import get_ai_reply, build_system_prompt
from services.ai_vision import describe_image

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.photo)
async def handle_photo(message: types.Message, bot: Bot):
    if message.from_user is None:
        return

    if not message.photo:
        return

    user_id = message.from_user.id

    await bot.send_chat_action(message.chat.id, "typing")

    # Берём фото в максимальном доступном качестве (последнее в списке размеров)
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)

    if file.file_path is None:
        await message.answer("Не смог скачать фото, попробуй ещё раз.")
        return

    file_bytes_io = await bot.download_file(file.file_path)

    if file_bytes_io is None:
        await message.answer("Не смог скачать фото, попробуй ещё раз.")
        return

    image_bytes = file_bytes_io.read()

    # Шаг 1: получаем описание фото от vision-модели
    description = describe_image(image_bytes)
    logger.debug("Vision description: %s", description)

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

    ai_answer = get_ai_reply(messages)

    save_message(user_id, "assistant", ai_answer)

    await message.answer(ai_answer)
