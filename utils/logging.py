"""
Настройка логирования с интеграцией ELK Stack
"""
import os
import logging
import sys
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger
import httpx
from datetime import datetime

# Настройки ELK Stack
LOGSTASH_HOST = os.getenv("LOGSTASH_HOST", "localhost")
LOGSTASH_PORT = int(os.getenv("LOGSTASH_PORT", "5044"))
LOGSTASH_ENABLED = os.getenv("LOGSTASH_ENABLED", "true").lower() == "true"


class LogstashHandler(logging.Handler):
    """Handler для отправки логов в Logstash"""

    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.url = f"http://{host}:{port}"

    def emit(self, record):
        """Отправка лога в Logstash"""
        try:
            log_entry = self.format(record)
            if isinstance(log_entry, str):
                import json
                log_entry = json.loads(log_entry)
            
            # Добавляем метаданные
            log_entry['@timestamp'] = datetime.utcnow().isoformat()
            log_entry['host'] = os.getenv('HOSTNAME', 'unknown')
            
            # Отправка через HTTP
            with httpx.Client(timeout=1.0) as client:
                client.post(self.url, json=log_entry)
        except Exception:
            # Игнорируем ошибки отправки, чтобы не ломать приложение
            pass


def setup_logging(log_level=logging.INFO):
    """Настройка логирования"""
    # Форматтер для JSON логов
    json_formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        timestamp=True
    )
    
    # Форматтер для консольных логов
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Консольный handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Файловый handler с ротацией
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(json_formatter)
    root_logger.addHandler(file_handler)
    
    # Logstash handler (если включен)
    if LOGSTASH_ENABLED:
        try:
            logstash_handler = LogstashHandler(LOGSTASH_HOST, LOGSTASH_PORT)
            logstash_handler.setFormatter(json_formatter)
            root_logger.addHandler(logstash_handler)
        except Exception as e:
            print(f"Warning: Could not setup Logstash handler: {e}")


def get_logger(name: str) -> logging.Logger:
    """Получение логгера"""
    return logging.getLogger(name)
