""" 
Middleware для управления сессиями базы данных в жизненном цикле запроса.
Обеспечивает автоматическое создание и закрытие сессии для каждого входящего события.
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from models import AsyncSessionLocal

class DbSessionMiddleware(BaseMiddleware):
    """
    Инжектирует асинхронную сессию SQLAlchemy в хендлеры через аргумент 'db'.
    Гарантирует закрытие сессии даже при возникновении исключений в хендлере.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Открытие сессии из глобальной фабрики
        async with AsyncSessionLocal() as session:
            data["db"] = session
            try:
                # Передача управления следующему middleware или хендлеру
                return await handler(event, data)
            except Exception as e:
                # Логирование на уровне middleware может быть добавлено здесь
                raise e
            finally:
                # Сессия закрывается автоматически контекстным менеджером, 
                # но явный вызов полезен для читаемости архитектуры.
                await session.close()
