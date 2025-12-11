"""
Тесты для базы данных
"""
import pytest
from bot.database.sqlite_db import SQLiteTicketDatabase
from bot.ticket_models import Ticket, TicketClassification, TicketType, TicketPriority, TicketStatus
from datetime import datetime


class TestSQLiteDatabase:
    """Тесты для SQLite базы данных"""
    
    def test_create_ticket(self, test_db_path, sample_ticket):
        """Тест создания тикета"""
        db = SQLiteTicketDatabase(db_path=test_db_path)
        
        created_ticket = db.create_ticket(sample_ticket)
        
        assert created_ticket.id is not None
        assert created_ticket.ticket_number is not None
        assert created_ticket.user_id == sample_ticket.user_id
    
    def test_get_ticket(self, test_db_path, sample_ticket):
        """Тест получения тикета"""
        db = SQLiteTicketDatabase(db_path=test_db_path)
        
        created_ticket = db.create_ticket(sample_ticket)
        retrieved_ticket = db.get_ticket(created_ticket.id)
        
        assert retrieved_ticket is not None
        assert retrieved_ticket.id == created_ticket.id
        assert retrieved_ticket.description == sample_ticket.description
    
    def test_get_tickets_by_user(self, test_db_path, sample_ticket):
        """Тест получения тикетов пользователя"""
        db = SQLiteTicketDatabase(db_path=test_db_path)
        
        # Создаем несколько тикетов
        ticket1 = db.create_ticket(sample_ticket)
        ticket2 = Ticket(
            id=2,
            ticket_number="#002",
            user_id=sample_ticket.user_id,
            username=sample_ticket.username,
            title="Вторая проблема",
            description="Описание второй проблемы",
            classification=sample_ticket.classification,
            support_line=1,
            status=TicketStatus.NEW,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.create_ticket(ticket2)
        
        # Тикет другого пользователя
        ticket3 = Ticket(
            id=3,
            ticket_number="#003",
            user_id=99999,
            username="other_user",
            title="Проблема другого пользователя",
            description="Описание",
            classification=sample_ticket.classification,
            support_line=1,
            status=TicketStatus.NEW,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.create_ticket(ticket3)
        
        user_tickets = db.get_tickets_by_user(sample_ticket.user_id)
        
        assert len(user_tickets) == 2
        assert all(t.user_id == sample_ticket.user_id for t in user_tickets)
    
    def test_get_tickets_by_line(self, test_db_path, sample_ticket):
        """Тест получения тикетов по линии поддержки"""
        db = SQLiteTicketDatabase(db_path=test_db_path)
        
        # Создаем тикеты для разных линий
        ticket1 = db.create_ticket(sample_ticket)  # Линия 1
        
        ticket2 = Ticket(
            id=2,
            ticket_number="#002",
            user_id=sample_ticket.user_id,
            username=sample_ticket.username,
            title="Проблема линии 2",
            description="Описание",
            classification=sample_ticket.classification,
            support_line=2,
            status=TicketStatus.NEW,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.create_ticket(ticket2)
        
        line1_tickets = db.get_tickets_by_line(1)
        line2_tickets = db.get_tickets_by_line(2)
        
        assert len(line1_tickets) == 1
        assert len(line2_tickets) == 1
        assert line1_tickets[0].support_line == 1
        assert line2_tickets[0].support_line == 2
    
    def test_update_ticket(self, test_db_path, sample_ticket):
        """Тест обновления тикета"""
        db = SQLiteTicketDatabase(db_path=test_db_path)
        
        created_ticket = db.create_ticket(sample_ticket)
        created_ticket.status = TicketStatus.IN_PROGRESS
        created_ticket.resolution = "Проблема решена"
        
        updated_ticket = db.update_ticket(created_ticket)
        
        retrieved_ticket = db.get_ticket(created_ticket.id)
        assert retrieved_ticket.status == TicketStatus.IN_PROGRESS
        assert retrieved_ticket.resolution == "Проблема решена"
    
    def test_get_queue_stats(self, test_db_path, sample_ticket):
        """Тест получения статистики очередей"""
        db = SQLiteTicketDatabase(db_path=test_db_path)
        
        # Создаем тикеты для разных линий и статусов
        ticket1 = db.create_ticket(sample_ticket)  # Линия 1, Новое
        
        ticket2 = Ticket(
            id=2,
            ticket_number="#002",
            user_id=sample_ticket.user_id,
            username=sample_ticket.username,
            title="Проблема линии 2",
            description="Описание",
            classification=sample_ticket.classification,
            support_line=2,
            status=TicketStatus.IN_PROGRESS,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.create_ticket(ticket2)
        
        stats = db.get_queue_stats()
        
        assert "line_1_pending" in stats
        assert "line_2_pending" in stats
        assert "line_3_pending" in stats
        assert stats["line_1_pending"] == 1
        assert stats["line_2_pending"] == 1
        assert stats["line_3_pending"] == 0
