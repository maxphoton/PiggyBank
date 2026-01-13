"""Утилита для рассылки сигналов пользователям."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import FSInputFile

from config import BROADCAST_LOGS_DIR
from database import get_all_users

logger = logging.getLogger(__name__)

# Словарь для хранения активных задач рассылки {admin_id: task}
active_broadcasts = {}


async def send_broadcast_task(
    bot: Bot,
    photo_file_id: str | None,
    caption: str,
    admin_id: int,
    parse_mode: str = "HTML",
):
    """
    Фоновая задача для отправки рассылки пользователям.
    Выполняется асинхронно и отправляет результат админу после завершения.
    """
    successful = 0
    failed = 0

    try:
        # Получаем всех пользователей из БД
        user_ids = await get_all_users()
        # Преобразуем в формат словарей для совместимости
        users = [{"telegram_id": user_id} for user_id in user_ids]

        total_users = len(users)

        # Создаем файл лога для этой рассылки
        log_file = (
            Path(BROADCAST_LOGS_DIR)
            / f"broadcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        # Формируем информацию о картинке (file_id - это внутренний идентификатор Telegram)
        photo_info = f"Photo file_id: {photo_file_id}"

        with open(log_file, "w", encoding="utf-8") as log:
            # Параметры сообщения в начале лога
            log.write("=" * 60 + "\n")
            log.write("ПАРАМЕТРЫ РАССЫЛКИ\n")
            log.write("=" * 60 + "\n")
            log.write(f"Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log.write(f"Админ ID: {admin_id}\n")
            log.write("Тип рассылки: Все пользователи из БД\n")
            log.write(f"Картинка (file_id): {photo_info}\n")
            log.write(f"Текст сообщения:\n{caption}\n")
            log.write(f"Количество получателей: {total_users}\n")
            log.write("=" * 60 + "\n\n")
            log.write("ЛОГ ОТПРАВКИ\n")
            log.write("=" * 60 + "\n")

            # Отправляем каждому пользователю
            for user in users:
                user_id = user["telegram_id"]
                try:
                    if photo_file_id:
                        await bot.send_photo(
                            chat_id=user_id,
                            photo=photo_file_id,
                            caption=caption,
                            parse_mode=parse_mode if parse_mode else None,
                        )
                    else:
                        await bot.send_message(
                            chat_id=user_id,
                            text=caption,
                            parse_mode=parse_mode if parse_mode else None,
                        )
                    successful += 1
                    log.write(f"User {user_id}: SUCCESS\n")
                    logger.debug(f"Sent signal to user {user_id}")
                except TelegramForbiddenError:
                    # Пользователь заблокировал бота
                    failed += 1
                    error_msg = "User blocked the bot"
                    log.write(f"User {user_id}: FAILED - {error_msg}\n")
                    logger.warning(f"User {user_id} blocked the bot")
                except TelegramBadRequest as e:
                    # Другая ошибка
                    failed += 1
                    error_msg = str(e)
                    log.write(f"User {user_id}: FAILED - {error_msg}\n")
                    logger.error(f"Failed to send to user {user_id}: {e}")
                except Exception as e:
                    # Неожиданная ошибка
                    failed += 1
                    error_msg = str(e)
                    log.write(f"User {user_id}: FAILED - {error_msg}\n")
                    logger.error(f"Unexpected error sending to user {user_id}: {e}")

                # Небольшая задержка между отправками
                await asyncio.sleep(0.05)

            log.write("\nSummary:\n")
            log.write(f"Successful: {successful}\n")
            log.write(f"Failed: {failed}\n")

        logger.info(f"Broadcast completed: {successful} successful, {failed} failed")

        # Отправляем результат админу
        result_text = (
            f"✅ Рассылка завершена!\n\n"
            f"Всего получателей: {total_users}\n"
            f"Успешно отправлено: {successful}\n"
            f"Ошибок: {failed}"
        )

        try:
            await bot.send_message(admin_id, result_text)

            # Отправляем файл лога
            if log_file.exists():
                document = FSInputFile(str(log_file))
                await bot.send_document(
                    chat_id=admin_id, document=document, caption="📄 Лог рассылки"
                )
        except Exception as e:
            logger.error(f"Failed to send result to admin {admin_id}: {e}")

    except asyncio.CancelledError:
        # Если задача была отменена
        logger.warning(f"Broadcast task was cancelled for admin {admin_id}")
        try:
            await bot.send_message(
                admin_id,
                f"❗️ Рассылка была принудительно остановлена.\n\n"
                f"✅ Успешно отправлено: {successful}\n"
                f"❌ Ошибок: {failed}",
            )
            # Отправляем файл лога, если он был создан
            if log_file.exists():
                document = FSInputFile(str(log_file))
                await bot.send_document(
                    chat_id=admin_id, document=document, caption="📄 Лог рассылки"
                )
        except Exception as e:
            logger.error(
                f"Failed to send cancellation message to admin {admin_id}: {e}"
            )
    except Exception as e:
        logger.error(f"Error in broadcast task: {e}", exc_info=True)
        try:
            await bot.send_message(admin_id, f"❌ Произошла ошибка при рассылке: {e}")
        except Exception:
            pass
    finally:
        # Очистка в любом случае
        if admin_id in active_broadcasts:
            del active_broadcasts[admin_id]
            logger.info(
                f"Broadcast task removed from active_broadcasts for admin {admin_id}"
            )


def start_broadcast_task(
    bot: Bot,
    photo_file_id: str | None,
    caption: str,
    admin_id: int,
    parse_mode: str = "HTML",
) -> asyncio.Task | None:
    """
    Запустить рассылку в фоновом режиме.

    Args:
        bot: Экземпляр бота
        photo_file_id: ID фото в Telegram
        caption: Текст подписи
        admin_id: ID админа, отправившего рассылку
        parse_mode: Режим парсинга (Markdown, HTML, None)

    Returns:
        asyncio.Task - задача рассылки или None, если уже есть активная рассылка
    """
    # Проверяем, есть ли уже активная рассылка для этого админа
    if admin_id in active_broadcasts:
        logger.warning(
            f"Admin {admin_id} tried to start broadcast while one is already active"
        )
        return None

    task = asyncio.create_task(
        send_broadcast_task(bot, photo_file_id, caption, admin_id, parse_mode)
    )
    active_broadcasts[admin_id] = task
    logger.info(f"Broadcast task started for admin {admin_id}")
    return task


def cancel_broadcast(admin_id: int) -> bool:
    """
    Отменить активную рассылку для админа.

    Args:
        admin_id: ID админа

    Returns:
        bool - True, если рассылка была отменена, False если не было активной рассылки
    """
    if admin_id in active_broadcasts:
        task = active_broadcasts[admin_id]
        task.cancel()
        logger.info(f"Broadcast cancellation requested for admin {admin_id}")
        return True
    return False


def has_active_broadcast(admin_id: int) -> bool:
    """
    Проверить, есть ли активная рассылка для админа.

    Args:
        admin_id: ID админа

    Returns:
        bool - True, если есть активная рассылка, False иначе
    """
    return admin_id in active_broadcasts
