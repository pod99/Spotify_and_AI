#!/bin/bash

# Принудительно убить все процессы, связанные с ботом
# Это убьет и run.py, и дочерний процесс spotify_auth_server.py
echo "Stopping all related bot processes..."
pkill -9 -f "spotify_and_yandex"

# Подождать секунду для надёжности
sleep 1

# Активировать виртуальное окружение
source venv/bin/activate

# Запустить run.py
echo "Starting bot..."
python run.py 