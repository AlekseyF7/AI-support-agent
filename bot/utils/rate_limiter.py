"""
Rate limiter для защиты от злоупотреблений
"""
import time
from typing import Dict, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter с поддержкой разных лимитов для разных действий"""
    
    def __init__(self):
        """Инициализация rate limiter"""
        # Словарь для хранения истории запросов: {user_id: {action: [timestamps]}}
        self._requests: Dict[int, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
        
        # Лимиты по умолчанию: {action: (max_requests, window_seconds)}
        self._limits: Dict[str, tuple] = {
            'message': (10, 60),  # 10 сообщений в минуту
            'rag_query': (20, 60),  # 20 запросов RAG в минуту
            'classification': (30, 60),  # 30 классификаций в минуту
            'ticket_creation': (5, 300),  # 5 тикетов в 5 минут
        }
    
    def set_limit(self, action: str, max_requests: int, window_seconds: int):
        """
        Установить лимит для действия
        
        Args:
            action: Название действия
            max_requests: Максимальное количество запросов
            window_seconds: Окно времени в секундах
        """
        self._limits[action] = (max_requests, window_seconds)
    
    def is_allowed(self, user_id: int, action: str = 'message') -> bool:
        """
        Проверить, разрешен ли запрос
        
        Args:
            user_id: ID пользователя
            action: Тип действия
            
        Returns:
            True если запрос разрешен, False если превышен лимит
        """
        if action not in self._limits:
            logger.warning(f"Неизвестное действие для rate limit: {action}")
            return True
        
        max_requests, window_seconds = self._limits[action]
        current_time = time.time()
        
        # Получаем историю запросов для пользователя и действия
        user_requests = self._requests[user_id][action]
        
        # Удаляем старые запросы вне окна
        user_requests[:] = [
            timestamp for timestamp in user_requests
            if current_time - timestamp < window_seconds
        ]
        
        # Проверяем лимит
        if len(user_requests) >= max_requests:
            logger.warning(
                f"Rate limit превышен для пользователя {user_id}, действие {action}: "
                f"{len(user_requests)}/{max_requests} запросов за {window_seconds} сек."
            )
            return False
        
        # Добавляем текущий запрос
        user_requests.append(current_time)
        return True
    
    def get_remaining(self, user_id: int, action: str = 'message') -> int:
        """
        Получить количество оставшихся запросов
        
        Args:
            user_id: ID пользователя
            action: Тип действия
            
        Returns:
            Количество оставшихся запросов
        """
        if action not in self._limits:
            return -1
        
        max_requests, window_seconds = self._limits[action]
        current_time = time.time()
        
        user_requests = self._requests[user_id][action]
        user_requests[:] = [
            timestamp for timestamp in user_requests
            if current_time - timestamp < window_seconds
        ]
        
        return max(0, max_requests - len(user_requests))
    
    def reset(self, user_id: Optional[int] = None, action: Optional[str] = None):
        """
        Сбросить счетчики
        
        Args:
            user_id: ID пользователя (если None, сбрасываются все)
            action: Действие (если None, сбрасываются все действия)
        """
        if user_id is None:
            self._requests.clear()
        elif action is None:
            if user_id in self._requests:
                self._requests[user_id].clear()
        else:
            if user_id in self._requests and action in self._requests[user_id]:
                self._requests[user_id][action].clear()
    
    def cleanup_old_entries(self, max_age_seconds: int = 3600):
        """
        Очистка старых записей
        
        Args:
            max_age_seconds: Максимальный возраст записи в секундах
        """
        current_time = time.time()
        users_to_remove = []
        
        for user_id, actions in self._requests.items():
            for action, timestamps in actions.items():
                timestamps[:] = [
                    ts for ts in timestamps
                    if current_time - ts < max_age_seconds
                ]
            
            # Удаляем пользователя если у него нет активных запросов
            if not any(actions.values()):
                users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            del self._requests[user_id]
    
    def get_stats(self) -> Dict[str, any]:
        """Получить статистику rate limiter"""
        return {
            'total_users': len(self._requests),
            'limits': dict(self._limits),
        }
