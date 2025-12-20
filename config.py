"""Конфигурация приложения с поддержкой UTF-8 и асинхронности."""
import sys
import io
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

# Настройка кодировки для Windows
# Настройка кодировки для Windows (только если не запущены тесты)
if sys.platform == 'win32' and "pytest" not in sys.modules:
    if hasattr(sys.stdout, 'buffer'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        except Exception:
            pass
    if hasattr(sys.stderr, 'buffer'):
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        except Exception:
            pass

class Settings(BaseSettings):
    # Giga Chat API
    GIGACHAT_CLIENT_ID: str = ""
    GIGACHAT_CLIENT_SECRET: str = ""
    GIGACHAT_AUTHORIZATION_KEY: str = ""
    GIGACHAT_SCOPE: str = "GIGACHAT_API_PERS"
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""
    
    # Sber Salute Speech
    SALUTE_SPEECH_CLIENT_ID: str = ""
    SALUTE_SPEECH_CLIENT_SECRET: str = ""
    
    # 2GIS API
    DG_API_KEY: str = ""
    
    # WebApp
    WEBAPP_URL: str = "http://localhost:8000"
    
    # Database & RAG
    DATABASE_URL: str = "sqlite+aiosqlite:///./support.db"
    CHROMA_DB_PATH: str = "./chroma_db"
    EMBEDDING_MODEL_NAME: str = "./models/rubert-tiny2"
    
    # Adaptive Intelligence (Autopilot)
    TARGET_SUCCESS_RATE: float = 0.80  # Целевой % автоматизации (80%)
    MIN_CONFIDENCE_THRESHOLD: int = 50 # Минимальный порог (смелый)
    MAX_CONFIDENCE_THRESHOLD: int = 90 # Максимальный порог (строгий)
    AI_CONFIDENCE_THRESHOLD: int = 70  # Стартовое значение

    # Shadow Hunter (Scraping)
    KNOWLEDGE_HUNT_INTERVAL: int = 24  # Интервал авто-парсинга в часах (0 - выключено)

    # Operators
    OPERATOR_IDS: str = ""

    @property
    def operator_list(self) -> list[int]:
        """Преобразование строки ID в список целых чисел."""
        if not self.OPERATOR_IDS:
            return []
        return [int(oid.strip()) for oid in self.OPERATOR_IDS.split(',') if oid.strip().isdigit()]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    def validate_settings(self):
        """Проверка минимально необходимых настроек."""
        missing = []
        if not self.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not (self.GIGACHAT_AUTHORIZATION_KEY or (self.GIGACHAT_CLIENT_ID and self.GIGACHAT_CLIENT_SECRET)):
            missing.append("GigaChat Credentials (ID/Secret or Auth Key)")
            
        # ПРОВЕРКА NGROK (Критично для Mini App)
        import os
        if not os.getenv("NGROK_AUTHTOKEN"):
            print("⚠️ ВНИМАНИЕ: NGROK_AUTHTOKEN не установлен в .env! Интерактивная карта (Mini App) не будет работать в Telegram.")
            
        if missing:
            print("❌ ОШИБКА КОНФИГУРАЦИИ")
            print(f"Отсутствуют: {', '.join(missing)}")
            print("\nВыполните: python manage.py env init")
            raise ValueError("Не все настройки заполнены")

settings = Settings()

def get_settings():
    settings.validate_settings()
    return settings
