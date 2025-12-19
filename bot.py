""" 
Главная точка входа в систему AI Support Agent.
Обеспечивает жизненный цикл бота, инъекцию зависимостей и управление сервисами.
"""
import asyncio
import logging
import sys
from typing import Dict, Any

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import settings
from models import init_db
from middlewares.db import DbSessionMiddleware
from handlers import common, admin, user

from gigachat_client import GigaChatClient
from rag_system import RAGSystem, MockRAGSystem, LocalEmbeddingFunction
from classifier import RequestClassifier
from escalation import EscalationSystem
from salute_speech_client import SaluteSpeechClient
from geo_service import GeoService

# Настройка системного логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("sber_support_bot")

async def on_shutdown(dispatcher: Dispatcher):
    """
    Грациозное завершение работы.
    Закрывает все активные соединения и освобождает ресурсы ИИ-сервисов.
    """
    logger.info("🛑 Инициировано завершение работы бота...")
    
    services_to_close = ["stt", "gigachat", "geo"]
    for service_name in services_to_close:
        service = dispatcher.workflow_data.get(service_name)
        if service:
            try:
                await service.close()
                logger.info(f"✅ Сервис {service_name} успешно остановлен.")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при остановке {service_name}: {e}")
            
    logger.info("✨ Все системные ресурсы освобождены. До встречи!")

async def main():
    """
    Основной цикл инициализации и запуска системы.
    """
    logger.info("🚀 Запуск AI Support Agent [Platinum Edition]...")

    # 0. Инициализация базы данных
    try:
        await init_db()
    except Exception as e:
        logger.error(f"❌ Критическая ошибка БД: {e}")
        return

    # 1. Инициализация платформенных сервисов
    logger.info("🧠 Подготовка интеллектуального ядра...")
    gigachat = GigaChatClient()
    
    # Модель эмбеддингов (общая для RAG и Escalation)
    try:
        embedding_func = LocalEmbeddingFunction()
    except Exception as e:
        logger.error(f"❌ Не удалось инициализировать локальные эмбеддинги: {e}")
        sys.exit(1)
    
    # RAG Система
    try:
        rag = RAGSystem(embedding_function=embedding_func)
    except Exception as e:
        logger.error(f"⚠️ RAG недоступен: {e}. Используется заглушка.")
        rag = MockRAGSystem()
        
    classifier = RequestClassifier(gigachat_client=gigachat)
    stt = SaluteSpeechClient(
        settings.SALUTE_SPEECH_CLIENT_ID,
        settings.SALUTE_SPEECH_CLIENT_SECRET
    )
    geo = GeoService(settings.DG_API_KEY)

    # 2. Конфигурация Bot API
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Dispatcher с инъекцией глобальных зависимостей
    dp = Dispatcher(
        gigachat=gigachat,
        rag=rag,
        classifier=classifier,
        stt=stt,
        geo=geo,
        local_emb_func=embedding_func
    )
    
    # Регистрация хуков завершения
    dp.shutdown.register(on_shutdown)

    # 3. Подключение Middleware
    dp.update.outer_middleware(DbSessionMiddleware())
    
    @dp.update.outer_middleware()
    async def global_escalation_middleware(handler, event, data):
        """Инжектирует систему эскалации во все события при наличии сессии БД."""
        if "db" in data:
            rag_obj = data.get("rag")
            emb_func = data.get("local_emb_func")
            chroma = rag_obj.chroma_client if hasattr(rag_obj, "chroma_client") else None
            
            data["escalation_system"] = EscalationSystem(
                data["db"], 
                chroma_client=chroma,
                embedding_func=emb_func
            )
        return await handler(event, data)

    # 4. Регистрация бизнес-логики (Роутеры)
    dp.include_router(common.router) # Информационные команды
    dp.include_router(admin.router)  # Панель оператора (защищена фильтрами)
    dp.include_router(user.router)   # Пользовательский интерфейс и ИИ

    # 5. Планировщик фоновых задач (Shadow Hunter)
    if settings.KNOWLEDGE_HUNT_INTERVAL > 0:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from sber_hunter import ShadowHunter
        
        scheduler = AsyncIOScheduler()
        hunter = ShadowHunter([
            "https://www.sberbank.ru/ru/person/help",
            "https://www.sberbank.ru/ru/person/contributions/finder/faq"
        ])
        
        # Запуск охоты раз в N часов
        scheduler.add_job(
            hunter.run_hunt, 
            "interval", 
            hours=settings.KNOWLEDGE_HUNT_INTERVAL,
            name="ShadowHunter_Periodic_Sync"
        )
        scheduler.start()
        logger.info(f"⏰ Авто-парсинг включен: каждые {settings.KNOWLEDGE_HUNT_INTERVAL} ч.")
    else:
        logger.info("⏰ Авто-парсинг выключен (KNOWLEDGE_HUNT_INTERVAL=0).")

    # 6. Старт поллинга
    logger.info("📡 Бот успешно запущен и ожидает сообщений.")
    
    try:
        # Сброс накопленных обновлений для чистого старта
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Бот остановлен пользователем.")
    except Exception as e:
        logger.critical(f"💀 Фатальный сбой системы: {e}", exc_info=True)
        sys.exit(1)
