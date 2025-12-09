#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Скрипт для запуска бота с исправлением переменных окружения"""

import os
import sys

# Исправление переменных окружения
if 'HF_HUB_DOWNLOAD_TIMEOUT' in os.environ:
    value = os.environ['HF_HUB_DOWNLOAD_TIMEOUT']
    # Если значение содержит знак равенства, исправляем
    if '=' in value:
        # Извлекаем только числовое значение
        try:
            numeric_value = value.split('=')[-1].strip()
            os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = numeric_value
        except:
            # Если не получается, удаляем переменную
            del os.environ['HF_HUB_DOWNLOAD_TIMEOUT']

# Обход проблемы с chromadb и Python 3.14
# Устанавливаем переменную окружения для chromadb
os.environ['CHROMA_SERVER_NOFILE'] = '1024'

# Теперь импортируем и запускаем основной код
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Проверка обязательных переменных
required_vars = ["TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print(f"Ошибка: отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
    print("Пожалуйста, создайте файл .env и заполните необходимые переменные.")
    sys.exit(1)

try:
    from bot.telegram_bot import SupportBot
    
    # Создание и запуск бота
    bot = SupportBot()
    bot.run()
    
except KeyboardInterrupt:
    print("\nОстановка бота...")
except Exception as e:
    print(f"Критическая ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

