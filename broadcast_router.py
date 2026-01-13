"""Роутер для рассылки с использованием FSM состояний."""

import logging

from aiogram import Bot, Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from broadcast import cancel_broadcast, has_active_broadcast, start_broadcast_task
from config import ADMIN_ID

logger = logging.getLogger(__name__)

# Создаем роутер для рассылки
broadcast_router = Router()


class BroadcastStates(StatesGroup):
    """Состояния для процесса рассылки."""

    waiting_message = State()  # Ожидание сообщения для рассылки
    preview = State()  # Предпросмотр сообщения
    confirmation = State()  # Подтверждение рассылки


def is_admin(message: types.Message) -> bool:
    """Проверка, является ли пользователь админом."""
    return message.from_user and message.from_user.id == ADMIN_ID


def create_broadcast_keyboard() -> types.InlineKeyboardMarkup:
    """Создает инлайн клавиатуру с кнопками для рассылки."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm")
    )
    builder.add(
        InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")
    )
    builder.adjust(2)  # 2 кнопки в ряд
    return builder.as_markup()


async def safe_edit_message(
    message: types.Message, text: str, parse_mode: str = "HTML"
) -> None:
    """
    Безопасное редактирование сообщения.
    Использует edit_text для текстовых сообщений и edit_caption для сообщений с фото.
    """
    try:
        # Проверяем, есть ли фото в сообщении
        if message.photo or (
            message.document
            and message.document.mime_type
            and message.document.mime_type.startswith("image/")
        ):
            # Если есть фото, редактируем подпись
            await message.edit_caption(caption=text, parse_mode=parse_mode)
        else:
            # Если нет фото, редактируем текст
            await message.edit_text(text=text, parse_mode=parse_mode)
    except Exception as e:
        # Если не удалось отредактировать, отправляем новое сообщение
        logger.warning(f"Не удалось отредактировать сообщение: {e}. Отправляем новое.")
        await message.answer(text, parse_mode=parse_mode)


@broadcast_router.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message, state: FSMContext):
    """Обработчик команды /broadcast для админа."""
    if not is_admin(message):
        return

    user = message.from_user
    logger.info(f"Команда /broadcast от админа {user.id}")

    # Проверяем, есть ли уже активная рассылка
    if has_active_broadcast(user.id):
        await message.answer(
            "⚠️ У вас уже есть активная рассылка. Дождитесь её завершения или используйте /cancel_broadcast для отмены.",
            parse_mode="HTML",
        )
        return

    # Переходим в состояние ожидания сообщения
    await state.set_state(BroadcastStates.waiting_message)
    keyboard = create_broadcast_keyboard()
    await message.answer(
        "📢 <b>Рассылка</b>\n\n"
        "Отправьте сообщение с текстом и/или фото для рассылки всем пользователям.",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@broadcast_router.message(Command("cancel_broadcast"))
async def cmd_cancel_broadcast(message: types.Message, state: FSMContext):
    """Обработчик команды /cancel_broadcast для админа."""
    if not is_admin(message):
        return

    user = message.from_user
    logger.info(f"Команда /cancel_broadcast от админа {user.id}")

    # Сбрасываем состояние
    await state.clear()

    # Отменяем активную рассылку
    if cancel_broadcast(user.id):
        await message.answer("✅ Активная рассылка отменена.", parse_mode="HTML")
    else:
        await message.answer("ℹ️ Нет активной рассылки для отмены.", parse_mode="HTML")


@broadcast_router.callback_query(
    lambda c: c.data == "broadcast_cancel", StateFilter(BroadcastStates)
)
async def callback_cancel(callback: types.CallbackQuery, state: FSMContext):
    """Отмена процесса рассылки из любого состояния через инлайн кнопку."""
    if not callback.from_user or callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    await state.clear()
    await safe_edit_message(
        callback.message, "❌ Процесс рассылки отменен.", parse_mode="HTML"
    )
    await callback.answer()


@broadcast_router.message(StateFilter(BroadcastStates.waiting_message))
async def handle_broadcast_message(message: types.Message, state: FSMContext):
    """Обработчик сообщения от админа для рассылки."""
    if not is_admin(message):
        return

    user = message.from_user
    admin_id = user.id

    # Проверяем, есть ли уже активная рассылка
    if has_active_broadcast(admin_id):
        await message.answer(
            "⚠️ У вас уже есть активная рассылка. Дождитесь её завершения.",
            parse_mode="HTML",
        )
        await state.clear()
        return

    # Получаем текст и фото
    caption = message.caption or message.text or ""
    photo_file_id = None

    if message.photo:
        # Берем фото наибольшего размера
        photo_file_id = message.photo[-1].file_id
    elif (
        message.document
        and message.document.mime_type
        and message.document.mime_type.startswith("image/")
    ):
        # Если это изображение как документ
        photo_file_id = message.document.file_id

    # Проверяем, что есть хотя бы текст или фото
    if not caption and not photo_file_id:
        await message.answer(
            "❌ Сообщение должно содержать текст и/или фото.",
            parse_mode="HTML",
        )
        return

    # Сохраняем данные в состояние
    await state.update_data(
        caption=caption,
        photo_file_id=photo_file_id,
    )

    # Переходим в состояние предпросмотра
    await state.set_state(BroadcastStates.preview)

    # Формируем предпросмотр
    preview_text = "📋 <b>Предпросмотр рассылки:</b>\n\n"
    if photo_file_id:
        preview_text += "📷 <b>Фото:</b> Да\n"
    preview_text += f"<b>Текст:</b>\n{caption}"

    # Создаем клавиатуру с кнопками
    keyboard = create_broadcast_keyboard()

    if photo_file_id:
        # Отправляем фото с предпросмотром
        await message.answer_photo(
            photo=photo_file_id,
            caption=preview_text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    else:
        # Отправляем только текст
        await message.answer(preview_text, parse_mode="HTML", reply_markup=keyboard)


@broadcast_router.callback_query(
    lambda c: c.data == "broadcast_confirm", StateFilter(BroadcastStates.preview)
)
async def callback_confirm(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение рассылки через инлайн кнопку."""
    if not callback.from_user or callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен.", show_alert=True)
        return

    admin_id = callback.from_user.id

    # Получаем данные из состояния
    data = await state.get_data()
    caption = data.get("caption", "")
    photo_file_id = data.get("photo_file_id")

    # Проверяем, есть ли уже активная рассылка
    if has_active_broadcast(admin_id):
        await safe_edit_message(
            callback.message,
            "⚠️ У вас уже есть активная рассылка. Дождитесь её завершения.",
            parse_mode="HTML",
        )
        await state.clear()
        await callback.answer()
        return

    # Запускаем рассылку
    task = start_broadcast_task(
        bot=bot,
        photo_file_id=photo_file_id,
        caption=caption,
        admin_id=admin_id,
        parse_mode="HTML",
    )

    if task:
        await safe_edit_message(
            callback.message,
            "✅ Рассылка запущена! Вы получите уведомление о завершении.",
            parse_mode="HTML",
        )
        logger.info(f"Рассылка запущена админом {admin_id}")
    else:
        await safe_edit_message(
            callback.message,
            "❌ Не удалось запустить рассылку. Возможно, уже есть активная рассылка.",
            parse_mode="HTML",
        )

    await callback.answer()
    # Очищаем состояние
    await state.clear()
