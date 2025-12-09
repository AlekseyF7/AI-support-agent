"""
Главный файл для запуска Telegram бота поддержки

ВНИМАНИЕ: Если у вас Python 3.14, используйте run_bot.py вместо этого файла
для автоматического исправления проблем совместимости.
"""
import os
import sys

# Предупреждение о Python 3.14
if sys.version_info >= (3, 14):
    print("⚠️  ВНИМАНИЕ: Обнаружен Python 3.14")
    print("ChromaDB может иметь проблемы совместимости с Python 3.14.")
    print("Рекомендуется использовать Python 3.11 или 3.12.")
    print("Или используйте run_bot.py для автоматического исправления проблем.")
    print()
    response = input("Продолжить? (y/n): ")
    if response.lower() != 'y':
        sys.exit(0)

from dotenv import load_dotenv
import os

# Загрузка переменных окружения
load_dotenv()

# Отключение аналитики PostHog в ChromaDB (убирает предупреждения)
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# Проверка обязательных переменных
required_vars = ["TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print(f"Ошибка: отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
    print("Пожалуйста, создайте файл .env и заполните необходимые переменные.")
    print("Пример файла .env:")
    print("TELEGRAM_BOT_TOKEN=your_token_here")
    print("OPENAI_API_KEY=your_key_here")
    print("")
    print("Если OpenAI API недоступен в вашем регионе, добавьте:")
    print("OPENAI_PROXY=http://proxy.example.com:8080")
    print("Подробнее см. PROXY_SETUP.md")
    sys.exit(1)

# Информация о прокси (если настроен)
if os.getenv("OPENAI_PROXY"):
    print(f"[INFO] Используется прокси для OpenAI API")
if os.getenv("OPENAI_BASE_URL"):
    print(f"[INFO] Используется альтернативный базовый URL: {os.getenv('OPENAI_BASE_URL')}")

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
    print("\nСовет: Попробуйте использовать run_bot.py или Python 3.11/3.12")
    sys.exit(1)

