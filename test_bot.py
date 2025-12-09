#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Тестовый скрипт для проверки работы бота"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

print("=" * 50)
print("Тест компонентов бота")
print("=" * 50)

# Проверка переменных окружения
print("\n1. Проверка переменных окружения...")
token = os.getenv("TELEGRAM_BOT_TOKEN")
api_key = os.getenv("OPENAI_API_KEY")

if token and token != "your_telegram_bot_token_here":
    print(f"   [OK] TELEGRAM_BOT_TOKEN: {token[:20]}...")
else:
    print("   [ERROR] TELEGRAM_BOT_TOKEN: не установлен")
    sys.exit(1)

if api_key and api_key != "your_openai_api_key_here":
    print(f"   [OK] OPENAI_API_KEY: {api_key[:20]}...")
else:
    print("   [ERROR] OPENAI_API_KEY: не установлен")
    sys.exit(1)

# Проверка импортов
print("\n2. Проверка импортов...")
try:
    from telegram import Update
    from telegram.ext import Application
    print("   [OK] python-telegram-bot")
except Exception as e:
    print(f"   [ERROR] python-telegram-bot: {e}")
    sys.exit(1)

try:
    import chromadb
    print("   [OK] chromadb")
except Exception as e:
    print(f"   [ERROR] chromadb: {e}")
    sys.exit(1)

try:
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    print("   [OK] langchain-openai")
except Exception as e:
    print(f"   [ERROR] langchain-openai: {e}")
    sys.exit(1)

# Проверка инициализации компонентов
print("\n3. Проверка инициализации компонентов...")
try:
    from bot.rag_system import RAGSystem
    print("   [OK] RAGSystem импортирован")
except Exception as e:
    print(f"   [ERROR] RAGSystem: {e}")
    sys.exit(1)

try:
    from bot.classifier import TicketClassifier
    print("   [OK] TicketClassifier импортирован")
except Exception as e:
    print(f"   [ERROR] TicketClassifier: {e}")
    sys.exit(1)

try:
    from bot.escalation import EscalationSystem
    print("   [OK] EscalationSystem импортирован")
except Exception as e:
    print(f"   [ERROR] EscalationSystem: {e}")
    sys.exit(1)

# Проверка базы знаний
print("\n4. Проверка базы знаний...")
import os
kb_path = "knowledge_base"
if os.path.exists(kb_path):
    files = []
    for root, dirs, filenames in os.walk(kb_path):
        for filename in filenames:
            if filename.endswith('.md'):
                files.append(os.path.join(root, filename))
    print(f"   [OK] Найдено {len(files)} документов в базе знаний")
else:
    print("   [ERROR] Директория knowledge_base не найдена")
    sys.exit(1)

print("\n" + "=" * 50)
print("[SUCCESS] Все проверки пройдены!")
print("=" * 50)
print("\nБот готов к запуску. Используйте:")
print("  python main.py")
print("или")
print("  start_bot.bat")

