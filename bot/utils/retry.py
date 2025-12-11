"""
Утилита для retry-логики с экспоненциальной задержкой
"""
import time
import logging
from typing import Callable, TypeVar, Optional, List
from functools import wraps

T = TypeVar('T')
logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Декоратор для повторных попыток с экспоненциальной задержкой
    
    Args:
        max_retries: Максимальное количество попыток
        initial_delay: Начальная задержка в секундах
        max_delay: Максимальная задержка в секундах
        exponential_base: База для экспоненциального роста задержки
        exceptions: Кортеж исключений, при которых нужно повторять попытку
        on_retry: Функция-колбэк, вызываемая при каждой повторной попытке
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        if on_retry:
                            on_retry(e, attempt + 1)
                        
                        logger.warning(
                            f"Попытка {attempt + 1}/{max_retries + 1} не удалась для {func.__name__}: {e}. "
                            f"Повтор через {delay:.2f} сек."
                        )
                        
                        time.sleep(delay)
                        delay = min(delay * exponential_base, max_delay)
                    else:
                        logger.error(
                            f"Все {max_retries + 1} попыток исчерпаны для {func.__name__}: {e}"
                        )
            
            # Если все попытки исчерпаны, пробрасываем последнее исключение
            raise last_exception
        
        return wrapper
    return decorator


class RetryableAPI:
    """Класс для работы с API с автоматическим retry"""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
    
    def call_with_retry(
        self,
        func: Callable[..., T],
        *args,
        exceptions: tuple = (Exception,),
        **kwargs
    ) -> T:
        """
        Вызывает функцию с retry-логикой
        
        Args:
            func: Функция для вызова
            *args: Позиционные аргументы
            exceptions: Исключения, при которых нужно повторять попытку
            **kwargs: Именованные аргументы
            
        Returns:
            Результат вызова функции
        """
        delay = self.initial_delay
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    logger.warning(
                        f"Попытка {attempt + 1}/{self.max_retries + 1} не удалась: {e}. "
                        f"Повтор через {delay:.2f} сек."
                    )
                    
                    time.sleep(delay)
                    delay = min(delay * self.initial_delay * (2 ** attempt), self.max_delay)
                else:
                    logger.error(f"Все {self.max_retries + 1} попыток исчерпаны: {e}")
        
        raise last_exception
