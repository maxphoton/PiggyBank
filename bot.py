import json
import asyncio
import logging
import os
import tempfile
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, ADMIN_ID, API_URL, DATA_FILE, LOG_FILE, TEST_API, TEST_API_FILE
from database import (
    init_db, save_user, toggle_subscription, get_user_subscriptions,
    get_subscribed_users, get_all_users, export_table_to_csv, get_bot_statistics
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'),  # mode='a' для дополнения логов
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def load_test_api_file():
    """Загрузка данных из test_api.json для тестового режима"""
    try:
        with open(TEST_API_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Проверка типа данных
            if not isinstance(data, list):
                logger.error(f"В файле {TEST_API_FILE} данные не являются списком, а {type(data)}")
                return None
            logger.debug(f"Данные загружены из {TEST_API_FILE}. Найдено активов: {len(data)}")
            return data
    except FileNotFoundError:
        logger.warning(f"Тестовый режим: файл {TEST_API_FILE} не найден")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка при чтении JSON файла {TEST_API_FILE}: {e}", exc_info=True)
        return None


async def fetch_assets():
    """Получение данных об активах с API или из файла (в тестовом режиме)"""
    # Если включен тестовый режим, загружаем данные из test_api.json
    if TEST_API:
        logger.info(f"Тестовый режим: загрузка данных из файла {TEST_API_FILE}")
        data = await load_test_api_file()
        if data is None:
            logger.warning(f"Тестовый режим: файл {TEST_API_FILE} не найден или пуст")
            return None
        logger.info(f"Тестовый режим: данные загружены из файла. Найдено активов: {len(data)}")
        return data
    
    # Обычный режим: запрос к API
    logger.info("Запрос данных с API")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL) as response:
                if response.status == 200:
                    data = await response.json()
                    # Проверка типа данных
                    if not isinstance(data, list):
                        logger.error(f"API вернул не список, а {type(data)}")
                        return None
                    logger.info(f"Данные успешно получены с API. Найдено активов: {len(data)}")
                    return data
                else:
                    logger.warning(f"Ошибка при получении данных с API. Статус: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Исключение при запросе к API: {e}", exc_info=True)
        return None


async def save_assets_to_json(data):
    """Сохранение данных в JSON файл"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug(f"Данные сохранены в {DATA_FILE}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных в JSON: {e}", exc_info=True)


async def load_assets_from_json():
    """Загрузка сохраненных данных из JSON файла"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Проверка типа данных
            if not isinstance(data, list):
                logger.error(f"В файле {DATA_FILE} данные не являются списком, а {type(data)}")
                return None
            logger.debug(f"Данные загружены из {DATA_FILE}. Найдено активов: {len(data)}")
            return data
    except FileNotFoundError:
        logger.debug(f"Файл {DATA_FILE} не найден. Это нормально при первом запуске.")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка при чтении JSON файла: {e}", exc_info=True)
        return None




async def create_assets_keyboard(assets, user_id: int):
    """Создание инлайн клавиатуры с активами, у которых есть ключ epoch"""
    builder = InlineKeyboardBuilder()
    
    # Получаем подписки пользователя
    subscriptions = await get_user_subscriptions(user_id)
    
    for asset in assets:
        if 'epoch' in asset and 'asset_name' in asset:
            asset_ticker = asset.get('asset_ticker', 'unknown')
            asset_name = asset.get('asset_name', 'Unknown')
            
            # Проверяем, подписан ли пользователь
            is_subscribed = asset_ticker in subscriptions
            checkbox = "✅" if is_subscribed else "☐"
            
            builder.add(InlineKeyboardButton(
                text=f"{checkbox} {asset_name}",
                callback_data=f"toggle_{asset_ticker}"
            ))
    
    builder.adjust(1)  # 1 кнопка в ряд для лучшей читаемости
    return builder.as_markup()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user = message.from_user
    if not user:
        logger.warning("Команда /start от пользователя без информации")
        return
    
    logger.info(f"Команда /start от пользователя {user.id} (@{user.username})")
    
    # Сохранение пользователя в базу данных
    await save_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    logger.debug(f"Пользователь {user.id} сохранен в базу данных")
    
    # Получение данных с API
    assets_data = await fetch_assets()
    
    if assets_data is None:
        logger.warning(f"Не удалось получить данные с API для пользователя {user.id}")
        await message.answer("❌ Failed to fetch data from API. Please try again later.", parse_mode='HTML')
        return
    
    # Сохранение данных в JSON
    await save_assets_to_json(assets_data)
    
    # Фильтрация активов с ключом epoch
    assets_with_epoch = [asset for asset in assets_data if 'epoch' in asset]
    logger.info(f"Найдено активов с epoch: {len(assets_with_epoch)}")
    
    if not assets_with_epoch:
        await message.answer("ℹ️ No assets with 'epoch' key found.", parse_mode='HTML')
        return
    
    # Создание клавиатуры
    keyboard = await create_assets_keyboard(assets_with_epoch, user.id)
    
    # Отправка сообщения с кнопками
    text = f"""📊 Select assets to receive notifications:

Found assets: {len(assets_with_epoch)}
Click on an asset to enable/disable notifications"""
    
    await message.answer(text, reply_markup=keyboard, parse_mode='HTML')
    logger.debug(f"Сообщение с клавиатурой отправлено пользователю {user.id}")


@dp.message(Command("demo"))
async def cmd_demo(message: types.Message):
    """Обработчик команды /demo - демонстрация всех типов уведомлений"""
    user = message.from_user
    if not user:
        return
    
    logger.info(f"Команда /demo от пользователя {user.id} (@{user.username})")
    
    # Демонстрационные данные
    demo_asset_name = "Circle USD"
    demo_ticker = "USDC"
    demo_old_epoch = 34
    demo_new_epoch = 35
    demo_free_space = 50000
    
    demo_notifications = [
        {
            'type': 'epoch_appeared',
            'message': f"🆕 New asset added <b>{demo_asset_name}</b>!\nFree space: {demo_free_space}\n\nUse /start to configure notifications for this asset.\n\n<a href=\"https://app.piggybank.fi/\">Open PiggyBank</a>\n\n<i>⚠️ This is a demo notification</i>"
        },
        {
            'type': 'epoch_changed',
            'message': f"🔄 New Epoch for <b>{demo_asset_name}</b>: {demo_old_epoch} → {demo_new_epoch}\nFree space: {demo_free_space}\n\n<a href=\"https://app.piggybank.fi/\">Open PiggyBank</a>\n\n<i>⚠️ This is a demo notification</i>"
        },
        {
            'type': 'space_available',
            'message': f"✅ Space available for <b>{demo_asset_name}</b>! Free: {demo_free_space}\n\n<a href=\"https://app.piggybank.fi/\">Open PiggyBank</a>\n\n<i>⚠️ This is a demo notification</i>"
        }
    ]
    
    # Отправляем все демонстрационные уведомления с небольшой задержкой
    await message.answer("📋 <b>Demo Mode</b>\n\nSending all notification types...", parse_mode='HTML')
    
    for notification in demo_notifications:
        try:
            await message.answer(notification['message'], parse_mode='HTML')
            await asyncio.sleep(1)  # Задержка между сообщениями
        except Exception as e:
            logger.error(f"Ошибка при отправке демо-уведомления {notification['type']}: {e}", exc_info=True)
    
    logger.info(f"Демонстрационные уведомления отправлены пользователю {user.id}")


@dp.message(Command("get_data"))
async def cmd_get_data(message: types.Message):
    """Обработчик команды /get_data для админа"""
    user = message.from_user
    
    # Проверка, что команда от админа
    if not user or user.id != ADMIN_ID:
        return
    
    logger.info(f"Команда /get_data от админа {user.id}")
    
    try:
        # Отправляем сообщение о начале обработки
        processing_msg = await message.answer("⏳ Generating data export...", parse_mode='HTML')
        
        # Создаем временную директорию для CSV файлов
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_files = []
            
            # Экспортируем таблицы в CSV
            tables = ['users', 'user_subscriptions']
            for table in tables:
                csv_path = os.path.join(temp_dir, f'{table}.csv')
                try:
                    await export_table_to_csv(table, csv_path)
                    csv_files.append((csv_path, f'{table}.csv'))
                except Exception as e:
                    logger.error(f"Ошибка при экспорте таблицы {table}: {e}", exc_info=True)
                    await message.answer(f"❌ Error exporting table {table}: {e}", parse_mode='HTML')
            
            # Получаем статистику
            stats = await get_bot_statistics()
            
            # Формируем сообщение со статистикой
            stats_text = f"""📊 <b>Bot Statistics</b>

👥 <b>Users:</b>
• Total users: {stats['total_users']}
• Users with subscriptions: {stats['users_with_subscriptions']}

📋 <b>Subscriptions:</b>
• Total subscriptions: {stats['total_subscriptions']}
• Unique assets: {stats['unique_assets']}

🏆 <b>Top 5 Assets:</b>"""
            
            if stats['top_assets']:
                for i, (ticker, name, count) in enumerate(stats['top_assets'], 1):
                    asset_display = name if name else ticker
                    stats_text += f"\n{i}. {asset_display} ({ticker}): {count} subscribers"
            else:
                stats_text += "\nNo subscriptions yet"
            
            # Отправляем сообщение со статистикой
            await processing_msg.edit_text(stats_text, parse_mode='HTML')
            
            # Отправляем CSV файлы
            for csv_path, filename in csv_files:
                try:
                    file = FSInputFile(csv_path, filename=filename)
                    await message.answer_document(file)
                    logger.debug(f"CSV файл {filename} отправлен админу")
                except Exception as e:
                    logger.error(f"Ошибка при отправке CSV файла {filename}: {e}", exc_info=True)
                    await message.answer(f"❌ Error sending {filename}: {e}", parse_mode='HTML')
            
            # Отправляем файл логов, если он существует
            if os.path.exists(LOG_FILE) and os.path.isfile(LOG_FILE):
                try:
                    log_file = FSInputFile(LOG_FILE, filename='bot.log')
                    await message.answer_document(log_file)
                    logger.debug("Файл логов отправлен админу")
                except Exception as e:
                    logger.error(f"Ошибка при отправке файла логов: {e}", exc_info=True)
                    await message.answer(f"❌ Error sending log file: {e}", parse_mode='HTML')
            else:
                await message.answer("⚠️ Log file not found or is a directory", parse_mode='HTML')
        
        logger.info(f"Экспорт данных завершен для админа {user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении команды /get_data: {e}", exc_info=True)
        await message.answer(f"❌ Error: {e}", parse_mode='HTML')


@dp.callback_query(lambda c: c.data.startswith("toggle_"))
async def process_asset_toggle(callback: types.CallbackQuery):
    """Обработчик переключения подписки на актив"""
    user = callback.from_user
    asset_ticker = callback.data.replace("toggle_", "")
    logger.info(f"Переключение подписки на {asset_ticker} для пользователя {user.id}")
    
    # Загружаем данные об активах для получения названия
    assets_data = await fetch_assets()
    if assets_data is None:
        logger.warning(f"Не удалось загрузить данные для переключения подписки пользователя {user.id}")
        await callback.answer("❌ Error loading data", show_alert=True)
        return
    
    # Находим актив по тикеру
    asset = next((a for a in assets_data if a.get('asset_ticker') == asset_ticker), None)
    if not asset:
        logger.warning(f"Актив {asset_ticker} не найден для пользователя {user.id}")
        await callback.answer("❌ Asset not found", show_alert=True)
        return
    
    asset_name = asset.get('asset_name', asset_ticker)
    
    # Переключаем подписку
    is_subscribed = await toggle_subscription(user.id, asset_ticker, asset_name)
    
    if is_subscribed:
        logger.info(f"Пользователь {user.id} подписался на {asset_name} ({asset_ticker})")
        await callback.answer(f"✅ Notifications for {asset_name} enabled")
    else:
        logger.info(f"Пользователь {user.id} отписался от {asset_name} ({asset_ticker})")
        await callback.answer(f"☐ Notifications for {asset_name} disabled")
    
    # Обновляем клавиатуру
    assets_with_epoch = [a for a in assets_data if 'epoch' in a]
    new_keyboard = await create_assets_keyboard(assets_with_epoch, user.id)
    
    # Обновляем сообщение
    try:
        await callback.message.edit_reply_markup(reply_markup=new_keyboard)
        logger.debug(f"Клавиатура обновлена для пользователя {user.id}")
    except Exception as e:
        logger.warning(f"Не удалось обновить клавиатуру для пользователя {user.id}: {e}")
        # Если не удалось обновить (например, сообщение слишком старое), отправляем новое
        text = f"""📊 Select assets to receive notifications:

Found assets: {len(assets_with_epoch)}
Click on an asset to enable/disable notifications"""
        await callback.message.answer(
            text,
            reply_markup=new_keyboard,
            parse_mode='HTML'
        )


async def check_assets_changes():
    """Проверка изменений в активах и сбор списка уведомлений"""
    logger.info("Начало проверки изменений в активах")
    
    # Получаем текущие данные с API
    current_assets = await fetch_assets()
    if current_assets is None:
        logger.warning("Не удалось получить данные с API для проверки изменений")
        return []
    
    # Загружаем сохраненные данные
    saved_assets = await load_assets_from_json()
    if saved_assets is None:
        # Если нет сохраненных данных, просто сохраняем текущие
        logger.info("Сохраненных данных нет. Сохраняем текущие данные.")
        await save_assets_to_json(current_assets)
        return []
    
    notifications = []
    
    # Создаем словари для быстрого поиска по тикеру
    # Фильтруем активы с валидным тикером (не None и не пустая строка)
    saved_dict = {asset.get('asset_ticker'): asset for asset in saved_assets 
                  if asset.get('asset_ticker') and isinstance(asset.get('asset_ticker'), str)}
    current_dict = {asset.get('asset_ticker'): asset for asset in current_assets 
                    if asset.get('asset_ticker') and isinstance(asset.get('asset_ticker'), str)}
    
    logger.debug(f"Сравнение: сохранено {len(saved_dict)} активов, текущих {len(current_dict)} активов")
    
    # Получаем список всех пользователей один раз для оптимизации
    all_users = await get_all_users()
    
    # 1. Проверяем появление ключа epoch у существующих объектов или новых объектов с epoch
    for ticker, current_asset in current_dict.items():
        saved_asset = saved_dict.get(ticker)
        current_has_epoch = 'epoch' in current_asset
        saved_has_epoch = saved_asset and 'epoch' in saved_asset if saved_asset else False
        
        if current_has_epoch and not saved_has_epoch:
            # Появился ключ epoch
            asset_name = current_asset.get('asset_name', ticker)
            logger.info(f"Обнаружено появление epoch для актива {asset_name} ({ticker}). Пользователей для уведомления: {len(all_users)}")
            
            # Получаем информацию о свободном месте
            free_space_text = ""
            current_lst_cap = current_asset.get('lst_cap')
            current_lst_tvl = current_asset.get('lst_tvl')
            if current_lst_cap is not None and current_lst_tvl is not None:
                try:
                    free_space = int(current_lst_cap) - int(current_lst_tvl)
                    free_space_text = f"\nFree space: {free_space}"
                except (ValueError, TypeError):
                    pass
            
            notifications.append({
                'type': 'epoch_appeared',
                'asset_ticker': ticker,
                'asset_name': asset_name,
                'users': all_users,
                'message': f"🆕 New asset added <b>{asset_name}</b>!{free_space_text}\n\nUse /start to configure notifications for this asset.\n\n<a href=\"https://app.piggybank.fi/\">Open PiggyBank</a>"
            })
    
    # Проверяем новые объекты с epoch
    for ticker, current_asset in current_dict.items():
        if ticker not in saved_dict and 'epoch' in current_asset:
            asset_name = current_asset.get('asset_name', ticker)
            logger.info(f"Обнаружен новый актив с epoch: {asset_name} ({ticker}). Пользователей для уведомления: {len(all_users)}")
            
            # Получаем информацию о свободном месте
            free_space_text = ""
            current_lst_cap = current_asset.get('lst_cap')
            current_lst_tvl = current_asset.get('lst_tvl')
            if current_lst_cap is not None and current_lst_tvl is not None:
                try:
                    free_space = int(current_lst_cap) - int(current_lst_tvl)
                    free_space_text = f"\nFree space: {free_space}"
                except (ValueError, TypeError):
                    pass
            
            notifications.append({
                'type': 'new_asset_with_epoch',
                'asset_ticker': ticker,
                'asset_name': asset_name,
                'users': all_users,
                'message': f"🆕 New asset added: <b>{asset_name}</b>!{free_space_text}\n\nUse /start to configure notifications for this asset.\n\n<a href=\"https://app.piggybank.fi/\">Open PiggyBank</a>"
            })
    
    # 2. Проверяем изменение ключа epoch
    for ticker, current_asset in current_dict.items():
        saved_asset = saved_dict.get(ticker)
        if saved_asset and 'epoch' in current_asset and 'epoch' in saved_asset:
            current_epoch = current_asset.get('epoch')
            saved_epoch = saved_asset.get('epoch')
            
            if current_epoch != saved_epoch:
                asset_name = current_asset.get('asset_name', ticker)
                subscribed_users = await get_subscribed_users(ticker)
                if subscribed_users:
                    logger.info(f"Обнаружено изменение epoch для {asset_name} ({ticker}): {saved_epoch} → {current_epoch}. Подписчиков: {len(subscribed_users)}")
                    
                    # Получаем информацию о свободном месте
                    free_space_text = ""
                    current_lst_cap = current_asset.get('lst_cap')
                    current_lst_tvl = current_asset.get('lst_tvl')
                    if current_lst_cap is not None and current_lst_tvl is not None:
                        try:
                            free_space = int(current_lst_cap) - int(current_lst_tvl)
                            free_space_text = f"\nFree space: {free_space}"
                        except (ValueError, TypeError):
                            pass
                    
                    notifications.append({
                        'type': 'epoch_changed',
                        'asset_ticker': ticker,
                        'asset_name': asset_name,
                        'users': subscribed_users,
                        'old_epoch': saved_epoch,
                        'new_epoch': current_epoch,
                        'message': f"🔄 New Epoch for <b>{asset_name}</b>: {saved_epoch} → {current_epoch}{free_space_text}\n\n<a href=\"https://app.piggybank.fi/\">Open PiggyBank</a>"
                    })
    
    # 3. Проверяем изменения lst_tvl и появление свободного места
    for ticker, current_asset in current_dict.items():
        saved_asset = saved_dict.get(ticker)
        if saved_asset:
            current_lst_cap = current_asset.get('lst_cap')
            current_lst_tvl = current_asset.get('lst_tvl')
            saved_lst_cap = saved_asset.get('lst_cap')
            saved_lst_tvl = saved_asset.get('lst_tvl')
            
            # Проверяем, что все значения существуют
            if all(x is not None for x in [current_lst_cap, current_lst_tvl, saved_lst_cap, saved_lst_tvl]):
                try:
                    # Преобразование в float для сохранения десятичной части
                    current_cap_float = float(current_lst_cap)
                    current_tvl_float = float(current_lst_tvl)
                    saved_cap_float = float(saved_lst_cap)
                    saved_tvl_float = float(saved_lst_tvl)
                    
                    # Преобразование в int для проверки свободного места (с точностью до целых)
                    current_cap = int(current_cap_float)
                    current_tvl = int(current_tvl_float)
                    saved_cap = int(saved_cap_float)
                    saved_tvl = int(saved_tvl_float)
                    
                    # Логируем любое изменение lst_tvl (с учетом десятичной части)
                    if current_tvl_float != saved_tvl_float:
                        asset_name = current_asset.get('asset_name', ticker)
                        change = current_tvl_float - saved_tvl_float
                        change_sign = "+" if change > 0 else ""
                        logger.info(f"Изменение lst_tvl для {asset_name} ({ticker}): {saved_tvl_float} → {current_tvl_float} ({change_sign}{change})")
                        
                        # Отправляем уведомление админу с десятичной частью
                        if ADMIN_ID:
                            try:
                                change_text = f"{change_sign}{change}" if change != 0 else "0"
                                admin_message = f"📊 <b>lst_tvl changed</b>\n\nAsset: <b>{asset_name}</b> ({ticker})\nOld value: {saved_tvl_float}\nNew value: {current_tvl_float}\nChange: {change_text}"
                                await bot.send_message(
                                    ADMIN_ID,
                                    admin_message,
                                    parse_mode='HTML'
                                )
                                logger.debug(f"Уведомление об изменении lst_tvl отправлено админу для {asset_name} ({ticker})")
                            except Exception as e:
                                logger.warning(f"Не удалось отправить уведомление админу об изменении lst_tvl: {e}")
                    
                    # Проверяем, что раньше было заполнено (lst_tvl == lst_cap с точностью до целых)
                    saved_was_full = saved_tvl == saved_cap
                    # Проверяем, что сейчас есть свободное место
                    current_has_space = current_tvl < current_cap
                    
                    if saved_was_full and current_has_space:
                        asset_name = current_asset.get('asset_name', ticker)
                        subscribed_users = await get_subscribed_users(ticker)
                        if subscribed_users:
                            free_space = current_cap - current_tvl
                            logger.info(f"Обнаружено свободное место для {asset_name} ({ticker}): {free_space}. Подписчиков: {len(subscribed_users)}")
                            notifications.append({
                                'type': 'space_available',
                                'asset_ticker': ticker,
                                'asset_name': asset_name,
                                'users': subscribed_users,
                                'free_space': free_space,
                                'message': f"✅ Space available for <b>{asset_name}</b>! Free: {free_space}\n\n<a href=\"https://app.piggybank.fi/\">Open PiggyBank</a>"
                            })
                except (ValueError, TypeError) as e:
                    logger.warning(f"Ошибка при преобразовании значений lst_cap/lst_tvl для {ticker}: {e}")
                    continue
    
    # 4. Обновляем сохраненные данные
    await save_assets_to_json(current_assets)
    
    if notifications:
        logger.info(f"Проверка завершена. Найдено изменений: {len(notifications)}")
    else:
        logger.debug("Проверка завершена. Изменений не обнаружено")
    
    return notifications


async def send_notifications(notifications):
    """Рассылка уведомлений пользователям в фоне"""
    logger.info(f"Начало рассылки уведомлений. Всего уведомлений: {len(notifications)}")
    
    total_sent = 0
    total_failed = 0
    
    for notification in notifications:
        notification_type = notification.get('type', 'unknown')
        users = notification.get('users', [])
        message_text = notification.get('message', '')
        asset_name = notification.get('asset_name', 'unknown')
        
        logger.info(f"Рассылка уведомления типа '{notification_type}' для актива {asset_name}. Получателей: {len(users)}")
        
        for user_id in users:
            try:
                await bot.send_message(
                    user_id,
                    message_text,
                    parse_mode='HTML'
                )
                total_sent += 1
                # Небольшая задержка, чтобы не перегружать API
                await asyncio.sleep(0.05)
            except Exception as e:
                total_failed += 1
                # Игнорируем ошибки отправки (пользователь заблокировал бота и т.д.)
                logger.warning(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
    
    logger.info(f"Рассылка завершена. Отправлено: {total_sent}, Ошибок: {total_failed}")


async def background_task():
    """Фоновая задача, выполняющаяся раз в минуту"""
    logger.info("Фоновая задача запущена")
    
    while True:
        try:
            # Собираем уведомления
            notifications = await check_assets_changes()
            
            # Рассылаем уведомления в фоне
            if notifications:
                logger.info(f"Запуск рассылки {len(notifications)} уведомлений в фоне")
                # Запускаем рассылку в отдельной задаче
                asyncio.create_task(send_notifications(notifications))
            
        except Exception as e:
            logger.error(f"Ошибка в фоновой задаче: {e}", exc_info=True)
        
        # Ждем минуту перед следующей проверкой
        logger.debug("Ожидание 60 секунд до следующей проверки")
        await asyncio.sleep(60)


async def main():
    """Главная функция"""
    logger.info("=" * 50)
    logger.info("Запуск бота - новая сессия")
    logger.info("=" * 50)
    
    # Проверка BOT_TOKEN
    if not BOT_TOKEN or BOT_TOKEN == '':
        logger.error("BOT_TOKEN не установлен! Установите токен в переменной окружения BOT_TOKEN")
        return
    
    # Инициализация базы данных
    logger.info("Инициализация базы данных")
    try:
        await init_db()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Критическая ошибка при инициализации БД: {e}", exc_info=True)
        return
    
    # Отправка сообщения админу о запуске бота
    if ADMIN_ID:
        try:
            await bot.send_message(
                ADMIN_ID,
                "✅ Bot has been started successfully!",
                parse_mode='HTML'
            )
            logger.info(f"Сообщение о запуске отправлено админу {ADMIN_ID}")
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение админу: {e}", exc_info=True)
    else:
        logger.warning("ADMIN_ID не указан, сообщение админу не отправлено")
    
    # Запуск фоновой задачи
    logger.info("Запуск фоновой задачи проверки изменений")
    asyncio.create_task(background_task())
    
    # Запуск бота
    logger.info("Бот запущен и готов к работе")
    await dp.start_polling(bot)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

