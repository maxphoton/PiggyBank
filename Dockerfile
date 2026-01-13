FROM python:3.13-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копирование файла зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY bot.py config.py database.py broadcast_router.py broadcast.py oinks.png ./

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=data

# Создание директории data (будет перезаписана volume, но нужно для первого запуска)
RUN mkdir -p /app/data && chmod 777 /app/data

# Запуск бота
CMD ["python", "bot.py"]

