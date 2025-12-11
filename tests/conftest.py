"""
Конфигурация pytest
"""
import pytest
import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Настройка переменных окружения для тестов
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test_token")
os.environ.setdefault("OPENAI_API_KEY", "test_key")
os.environ.setdefault("DB_TYPE", "sqlite")
os.environ.setdefault("LOG_LEVEL", "DEBUG")


@pytest.fixture
def test_db_path(tmp_path):
    """Путь к тестовой БД"""
    db_path = tmp_path / "test_tickets.db"
    return str(db_path)


@pytest.fixture
def sample_ticket():
    """Пример тикета для тестов"""
    from bot.ticket_models import Ticket, TicketClassification, TicketType, TicketPriority, TicketStatus
    from datetime import datetime
    
    classification = TicketClassification(
        theme="Техническая проблема",
        ticket_type=TicketType.INCIDENT,
        priority=TicketPriority.MEDIUM,
        system_service="Корпоративный портал",
        reasoning="Тестовое обращение"
    )
    
    return Ticket(
        id=1,
        ticket_number="#001",
        user_id=12345,
        username="test_user",
        title="Тестовая проблема",
        description="Описание тестовой проблемы",
        classification=classification,
        support_line=1,
        status=TicketStatus.NEW,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
