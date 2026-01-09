import os
from dotenv import load_dotenv

load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required. Please set it in .env file")

# Admin configuration
admin_id_str = os.getenv('ADMIN_ID', '')
if not admin_id_str or not admin_id_str.strip():
    raise ValueError("ADMIN_ID is required. Please set it in .env file")
ADMIN_ID = int(admin_id_str)

# API configuration
API_URL = os.getenv('API_URL', '')
# Test mode: if True, data will be loaded from saved file instead of API
TEST_API = os.getenv('TEST_API', 'false').lower() in ('true', '1', 'yes', 'on')
# Proxy configuration (optional)
PROXY = os.getenv('PROXY', '')

# Data directory configuration
DATA_DIR = os.getenv('DATA_DIR', '')
if DATA_DIR:
    # Создаем директорию, если она указана и не существует
    os.makedirs(DATA_DIR, exist_ok=True)
    DATA_FILE = os.path.join(DATA_DIR, 'assets_data.json')
    DB_FILE = os.path.join(DATA_DIR, 'users.db')
    LOG_FILE = os.path.join(DATA_DIR, 'bot.log')
else:
    # По умолчанию файлы в корне проекта
    DATA_FILE = os.getenv('DATA_FILE', 'assets_data.json')
    DB_FILE = os.getenv('DB_FILE', 'users.db')
    LOG_FILE = os.getenv('LOG_FILE', 'bot.log')

# Test API file path (определяется после DATA_DIR)
if DATA_DIR:
    TEST_API_FILE = os.path.join(DATA_DIR, 'test_api.json')
else:
    TEST_API_FILE = os.getenv('TEST_API_FILE', 'test_api.json')

