import logging

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

from database import clear_user_history, reset_user_profile, get_user_profile
from services.redis_client import get_redis

logger = logging.getLogger(__name__)
router = Router()


def _welcome_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Начать", callback_data="menu:main")],
    ])


def _main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Подписка", callback_data="menu:subscription")],
        [InlineKeyboardButton(text="🧠 Память бота", callback_data="menu:memory")],
        [InlineKeyboardButton(text="🗑 Очистить историю", callback_data="menu:clear_history")],
        [InlineKeyboardButton(text="✖️ Закрыть меню", callback_data="menu:close")],
    ])


def _subscription_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Купить подписку", callback_data="menu:buy_sub")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")],
    ])


def _confirm_clear_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data="menu:clear_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="menu:main"),
        ],
    ])


def _memory_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Очистить память", callback_data="menu:clear_history")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")],
    ])


WELCOME_TEXT = (
    "⚠️ <b>Внимание: контент 18+</b>\n\n"
    "Тебя приветствует <b>Виктор</b> — ИИ-собеседник без цензуры.\n\n"
    "• Грубый и саркастичный стиль общения\n"
    "• Мат и чёрный юмор как норма\n"
    "• Принимает <b>фотографии</b> и описывает их\n"
    "• Не подходит для слабонервных\n\n"
    "Нажми «Начать», если готов."
)

MAIN_TEXT = (
    "📋 <b>Главное меню</b>\n\n"
    "Выбери раздел ниже."
)

SUBSCRIPTION_TEXT = (
    "💎 <b>Подписка</b>\n\n"
    "Бесплатный тариф:\n"
    "• Ограниченное число сообщений\n"
    "• Базовая история диалога\n\n"
    "<b>Premium</b> <i>(скоро)</i>\n"
    "• Безлимитные сообщения\n"
    "• Расширенная история\n"
    "• Приоритетные ответы\n"
)

CLEAR_TEXT = (
    "🗑 <b>Очистка истории</b>\n\n"
    "Удалить всю историю переписки с Виктором?\n"
    "Действие необратимо."
)

MEMORY_TEXT = (
    "🧠 <b>Память бота</b>\n\n"
    "Виктор запоминает факты о тебе, чтобы давать более личные ответы.\n\n"
)


async def _build_memory_text(user_id: int) -> str:
    profile = await get_user_profile(user_id)
    name = profile.get("name", "")
    facts = profile.get("facts", "")

    parts = [MEMORY_TEXT]

    if name:
        parts.append(f"👤 <b>Имя:</b> {name}\n")
    else:
        parts.append("👤 <b>Имя:</b> <i>неизвестно</i>\n")

    if facts and facts.strip():
        parts.append("📝 <b>Запомненные факты:</b>\n")
        parts.append(facts)
    else:
        parts.append("📝 <b>Запомненные факты:</b> <i>пока пусто</i>")

    return "\n".join(parts)


async def _edit_or_answer(
    callback: types.CallbackQuery,
    text: str,
    kb: InlineKeyboardMarkup,
) -> None:
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(WELCOME_TEXT, reply_markup=_welcome_kb(), parse_mode="HTML")


@router.message(Command("menu"))
async def cmd_menu(message: types.Message):
    await message.answer(MAIN_TEXT, reply_markup=_main_kb(), parse_mode="HTML")


@router.message(Command("subscription"))
async def cmd_subscription(message: types.Message):
    await message.answer(SUBSCRIPTION_TEXT, reply_markup=_subscription_kb(), parse_mode="HTML")


@router.message(Command("memory"))
async def cmd_memory(message: types.Message):
    if message.from_user is None:
        return
    text = await _build_memory_text(message.from_user.id)
    await message.answer(text, reply_markup=_memory_kb(), parse_mode="HTML")


@router.callback_query(F.data == "menu:main")
async def cq_main(callback: types.CallbackQuery):
    await _edit_or_answer(callback, MAIN_TEXT, _main_kb())


@router.callback_query(F.data == "menu:subscription")
async def cq_subscription(callback: types.CallbackQuery):
    await _edit_or_answer(callback, SUBSCRIPTION_TEXT, _subscription_kb())


@router.callback_query(F.data == "menu:memory")
async def cq_memory(callback: types.CallbackQuery):
    text = await _build_memory_text(callback.from_user.id)
    await _edit_or_answer(callback, text, _memory_kb())


@router.callback_query(F.data == "menu:buy_sub")
async def cq_buy_sub(callback: types.CallbackQuery):
    await _edit_or_answer(
        callback,
        "🚧 <b>Покупка подписки будет доступна совсем скоро.</b>\n\n"
        "Мы уже готовим платёжную систему. Оставайтесь на связи!",
        _subscription_kb(),
    )


@router.callback_query(F.data == "menu:clear_history")
async def cq_clear_history(callback: types.CallbackQuery):
    await _edit_or_answer(callback, CLEAR_TEXT, _confirm_clear_kb())


@router.callback_query(F.data == "menu:clear_confirm")
async def cq_clear_confirm(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    await clear_user_history(user_id)
    await reset_user_profile(user_id)

    r = get_redis()
    await r.delete(f"profile:{user_id}")

    await _edit_or_answer(
        callback,
        "✅ <b>История удалена</b>\n\n"
        "Виктор ничего не помнит о прошлых разговорах.\n"
        "Можешь начать с чистого листа.",
        _main_kb(),
    )


@router.callback_query(F.data == "menu:close")
async def cq_close(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await callback.answer()
