import csv
import logging

import aiosqlite

from config import DB_FILE

logger = logging.getLogger(__name__)


async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                asset_ticker TEXT NOT NULL,
                asset_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, asset_ticker),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.commit()


async def save_user(
    user_id: int, username: str = None, first_name: str = None, last_name: str = None
):
    """Сохранение пользователя в базу данных"""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            """,
                (user_id, username, first_name, last_name),
            )
            await db.commit()
    except Exception as e:
        logger.error(
            f"Ошибка при сохранении пользователя {user_id}: {e}", exc_info=True
        )
        raise


async def toggle_subscription(user_id: int, asset_ticker: str, asset_name: str = None):
    """Переключение подписки пользователя на актив"""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            # Проверяем, есть ли уже подписка
            cursor = await db.execute(
                """
                SELECT id FROM user_subscriptions 
                WHERE user_id = ? AND asset_ticker = ?
            """,
                (user_id, asset_ticker),
            )
            existing = await cursor.fetchone()

            if existing:
                # Удаляем подписку
                await db.execute(
                    """
                    DELETE FROM user_subscriptions 
                    WHERE user_id = ? AND asset_ticker = ?
                """,
                    (user_id, asset_ticker),
                )
                await db.commit()
                return False  # Подписка отменена
            else:
                # Добавляем подписку
                await db.execute(
                    """
                    INSERT INTO user_subscriptions (user_id, asset_ticker, asset_name)
                    VALUES (?, ?, ?)
                """,
                    (user_id, asset_ticker, asset_name),
                )
                await db.commit()
                return True  # Подписка добавлена
    except Exception as e:
        logger.error(
            f"Ошибка при переключении подписки пользователя {user_id} на {asset_ticker}: {e}",
            exc_info=True,
        )
        raise


async def get_user_subscriptions(user_id: int):
    """Получение списка подписок пользователя"""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            cursor = await db.execute(
                """
                SELECT asset_ticker FROM user_subscriptions 
                WHERE user_id = ?
            """,
                (user_id,),
            )
            rows = await cursor.fetchall()
            return {row[0] for row in rows}  # Возвращаем set для быстрой проверки
    except Exception as e:
        logger.error(
            f"Ошибка при получении подписок пользователя {user_id}: {e}", exc_info=True
        )
        return set()  # Возвращаем пустой set при ошибке


async def get_subscribed_users(asset_ticker: str):
    """Получение списка пользователей, подписанных на конкретный актив"""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            cursor = await db.execute(
                """
                SELECT user_id FROM user_subscriptions 
                WHERE asset_ticker = ?
            """,
                (asset_ticker,),
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]  # Возвращаем список user_id
    except Exception as e:
        logger.error(
            f"Ошибка при получении подписчиков актива {asset_ticker}: {e}",
            exc_info=True,
        )
        return []  # Возвращаем пустой список при ошибке


async def get_all_users():
    """Получение списка всех пользователей"""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            cursor = await db.execute("""
                SELECT user_id FROM users
            """)
            rows = await cursor.fetchall()
            return [row[0] for row in rows]  # Возвращаем список user_id
    except Exception as e:
        logger.error(
            f"Ошибка при получении списка всех пользователей: {e}", exc_info=True
        )
        return []  # Возвращаем пустой список при ошибке


async def export_table_to_csv(table_name: str, csv_file_path: str):
    """Экспорт таблицы в CSV файл"""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            # Получаем данные из таблицы
            cursor = await db.execute(f"SELECT * FROM {table_name}")
            rows = await cursor.fetchall()

            # Получаем названия колонок
            cursor = await db.execute(f"PRAGMA table_info({table_name})")
            columns_info = await cursor.fetchall()
            column_names = [col[1] for col in columns_info]

            # Записываем в CSV
            with open(csv_file_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                # Записываем заголовки
                writer.writerow(column_names)
                # Записываем данные
                writer.writerows(rows)

            logger.info(
                f"Таблица {table_name} экспортирована в {csv_file_path}. Записей: {len(rows)}"
            )
            return len(rows)
    except Exception as e:
        logger.error(f"Ошибка при экспорте таблицы {table_name}: {e}", exc_info=True)
        raise


async def get_bot_statistics():
    """Получение статистики по боту"""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            # Количество пользователей
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            total_users = (await cursor.fetchone())[0]

            # Количество активных подписок
            cursor = await db.execute("SELECT COUNT(*) FROM user_subscriptions")
            total_subscriptions = (await cursor.fetchone())[0]

            # Количество уникальных активов с подписками
            cursor = await db.execute(
                "SELECT COUNT(DISTINCT asset_ticker) FROM user_subscriptions"
            )
            unique_assets = (await cursor.fetchone())[0]

            # Пользователи с подписками
            cursor = await db.execute(
                "SELECT COUNT(DISTINCT user_id) FROM user_subscriptions"
            )
            users_with_subscriptions = (await cursor.fetchone())[0]

            # Топ активов по подпискам
            cursor = await db.execute("""
                SELECT asset_ticker, asset_name, COUNT(*) as count 
                FROM user_subscriptions 
                GROUP BY asset_ticker, asset_name 
                ORDER BY count DESC 
                LIMIT 5
            """)
            top_assets = await cursor.fetchall()

            return {
                "total_users": total_users,
                "total_subscriptions": total_subscriptions,
                "unique_assets": unique_assets,
                "users_with_subscriptions": users_with_subscriptions,
                "top_assets": top_assets,
            }
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}", exc_info=True)
        raise
