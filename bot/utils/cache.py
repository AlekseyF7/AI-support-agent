"""
Менеджер кэширования для ответов LLM и других данных
"""
import hashlib
import json
import time
import os
from typing import Optional, Any, Dict
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """Менеджер кэширования с поддержкой in-memory и Redis (опционально)"""
    
    def __init__(self, use_redis: bool = False, redis_url: Optional[str] = None, default_ttl: int = 3600):
        """
        Инициализация менеджера кэша
        
        Args:
            use_redis: Использовать ли Redis для кэширования
            redis_url: URL Redis (если не указан, берется из REDIS_URL env)
            default_ttl: Время жизни кэша по умолчанию в секундах
        """
        self.default_ttl = default_ttl
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self.use_redis = use_redis
        
        if use_redis:
            redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
            try:
                import redis
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info(f"Redis подключен: {redis_url}")
            except ImportError:
                logger.warning("Redis не установлен. Используется in-memory кэш.")
                self.use_redis = False
            except Exception as e:
                logger.warning(f"Не удалось подключиться к Redis: {e}. Используется in-memory кэш.")
                self.use_redis = False
        else:
            self.redis_client = None
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Создает ключ кэша из аргументов"""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Получить значение из кэша
        
        Args:
            key: Ключ кэша
            
        Returns:
            Значение или None если не найдено или истек срок
        """
        if self.use_redis and self.redis_client:
            try:
                cached = self.redis_client.get(key)
                if cached:
                    data = json.loads(cached)
                    return data.get('value')
            except Exception as e:
                logger.warning(f"Ошибка чтения из Redis: {e}")
        
        # In-memory кэш
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if time.time() < entry['expires_at']:
                return entry['value']
            else:
                del self._memory_cache[key]
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Сохранить значение в кэш
        
        Args:
            key: Ключ кэша
            value: Значение для кэширования
            ttl: Время жизни в секундах (если None, используется default_ttl)
            
        Returns:
            True если успешно сохранено
        """
        ttl = ttl or self.default_ttl
        
        if self.use_redis and self.redis_client:
            try:
                data = {'value': value, 'cached_at': time.time()}
                self.redis_client.setex(key, ttl, json.dumps(data, ensure_ascii=False))
                return True
            except Exception as e:
                logger.warning(f"Ошибка записи в Redis: {e}")
        
        # In-memory кэш
        self._memory_cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl,
            'cached_at': time.time()
        }
        
        # Очистка старых записей (если кэш слишком большой)
        if len(self._memory_cache) > 10000:
            self._cleanup_expired()
        
        return True
    
    def delete(self, key: str) -> bool:
        """Удалить значение из кэша"""
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Ошибка удаления из Redis: {e}")
        
        if key in self._memory_cache:
            del self._memory_cache[key]
        
        return True
    
    def clear(self, prefix: Optional[str] = None) -> int:
        """
        Очистить кэш
        
        Args:
            prefix: Префикс для очистки (если None, очищается весь кэш)
            
        Returns:
            Количество удаленных записей
        """
        count = 0
        
        if self.use_redis and self.redis_client:
            try:
                if prefix:
                    keys = self.redis_client.keys(f"{prefix}:*")
                    if keys:
                        count = self.redis_client.delete(*keys)
                else:
                    self.redis_client.flushdb()
                    count = -1  # Неизвестно сколько удалено
            except Exception as e:
                logger.warning(f"Ошибка очистки Redis: {e}")
        
        if prefix:
            keys_to_delete = [k for k in self._memory_cache.keys() if k.startswith(prefix)]
            for key in keys_to_delete:
                del self._memory_cache[key]
                count += len(keys_to_delete)
        else:
            count = len(self._memory_cache)
            self._memory_cache.clear()
        
        return count
    
    def _cleanup_expired(self):
        """Очистка истекших записей из in-memory кэша"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._memory_cache.items()
            if entry['expires_at'] < current_time
        ]
        for key in expired_keys:
            del self._memory_cache[key]
    
    def cache_result(self, prefix: str = "cache", ttl: Optional[int] = None):
        """
        Декоратор для кэширования результатов функции
        
        Args:
            prefix: Префикс для ключей кэша
            ttl: Время жизни кэша в секундах
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Исключаем self из ключа кэша
                cache_key = self._make_key(prefix, *args[1:], **kwargs)
                
                # Пытаемся получить из кэша
                cached = self.get(cache_key)
                if cached is not None:
                    logger.debug(f"Кэш попадание для {func.__name__}")
                    return cached
                
                # Выполняем функцию и кэшируем результат
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl=ttl)
                logger.debug(f"Результат {func.__name__} закэширован")
                
                return result
            
            return wrapper
        return decorator
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику кэша"""
        stats = {
            'memory_cache_size': len(self._memory_cache),
            'use_redis': self.use_redis,
        }
        
        if self.use_redis and self.redis_client:
            try:
                stats['redis_info'] = self.redis_client.info('memory')
            except Exception:
                pass
        
        return stats
