"""
Настройка логирования для бота
"""
import logging
import sys
import os
from pathlib import Path
from typing import Optional
from datetime import datetime


def setup_logger(
    name: str = "support_bot",
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: str = "logs"
) -> logging.Logger:
    """
    Настройка логгера с детальным логированием
    
    Args:
        name: Имя логгера
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Путь к файлу логов (если None, создается автоматически)
        log_dir: Директория для логов
        
    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    
    # Не добавляем обработчики повторно если они уже есть
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, level.upper()))
    
    # Формат логов
    detailed_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_format)
    logger.addHandler(console_handler)
    
    # Файловый обработчик
    if log_file is None:
        log_dir_path = Path(log_dir)
        log_dir_path.mkdir(parents=True, exist_ok=True)
        log_file = log_dir_path / f"bot_{datetime.now().strftime('%Y%m%d')}.log"
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_format)
    logger.addHandler(file_handler)
    
    # Обработчик для ошибок
    error_log_file = Path(log_file).parent / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
    error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_format)
    logger.addHandler(error_handler)
    
    return logger


def get_logger(name: str = "support_bot") -> logging.Logger:
    """
    Получить логгер (создает если не существует)
    
    Args:
        name: Имя логгера
        
    Returns:
        Логгер
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Настройка по умолчанию
        log_level = os.getenv("LOG_LEVEL", "INFO")
        setup_logger(name, log_level)
    return logger
