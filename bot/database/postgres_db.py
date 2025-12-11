"""
PostgreSQL реализация базы данных тикетов
"""
import os
import json
from typing import List, Optional, Dict
from datetime import datetime

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

from .base_db import TicketDatabase
from ..ticket_models import Ticket, TicketStatus, TicketPriority, TicketType, TicketClassification


class PostgresTicketDatabase(TicketDatabase):
    """PostgreSQL реализация базы данных тикетов"""
    
    def __init__(self, database_url: Optional[str] = None):
        if not PSYCOPG2_AVAILABLE:
            raise ImportError(
                "psycopg2 не установлен. Установите его командой: pip install psycopg2-binary"
            )
        
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL не указан. Укажите URL PostgreSQL в переменных окружения."
            )
        
        self._init_database()
    
    def _get_connection(self):
        """Получить подключение к БД"""
        return psycopg2.connect(self.database_url)
    
    def _init_database(self):
        """Инициализация базы данных и создание таблиц"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Таблица тикетов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id SERIAL PRIMARY KEY,
                ticket_number VARCHAR(50) UNIQUE NOT NULL,
                user_id BIGINT NOT NULL,
                username VARCHAR(255),
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                theme VARCHAR(100) NOT NULL,
                ticket_type VARCHAR(50) NOT NULL,
                priority VARCHAR(50) NOT NULL,
                system_service VARCHAR(100),
                reasoning TEXT,
                support_line INTEGER NOT NULL,
                status VARCHAR(50) NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                rag_answer TEXT,
                conversation_history JSONB,
                resolved BOOLEAN DEFAULT FALSE,
                resolution TEXT,
                resolved_at TIMESTAMP,
                tags JSONB,
                assigned_to VARCHAR(255),
                escalation_reason TEXT,
                user_satisfaction VARCHAR(50)
            )
        """)
        
        # Индексы для быстрого поиска
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON tickets(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON tickets(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_support_line ON tickets(support_line)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_priority ON tickets(priority)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON tickets(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversation_history ON tickets USING GIN(conversation_history)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags ON tickets USING GIN(tags)")
        
        conn.commit()
        cursor.close()
        conn.close()
    
    def create_ticket(self, ticket: Ticket) -> Ticket:
        """Создание нового тикета"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Генерируем номер тикета если его нет
        if not ticket.ticket_number:
            cursor.execute("SELECT MAX(id) FROM tickets")
            last_id = cursor.fetchone()[0] or 0
            ticket.id = last_id + 1
            ticket.ticket_number = f"#{ticket.id:03d}"
        
        cursor.execute("""
            INSERT INTO tickets (
                ticket_number, user_id, username, title, description,
                theme, ticket_type, priority, system_service, reasoning,
                support_line, status, created_at, updated_at,
                rag_answer, conversation_history, resolved, resolution, resolved_at,
                tags, assigned_to, escalation_reason, user_satisfaction
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            ticket.ticket_number,
            ticket.user_id,
            ticket.username,
            ticket.title,
            ticket.description,
            ticket.classification.theme,
            ticket.classification.ticket_type.value,
            ticket.classification.priority.value,
            ticket.classification.system_service,
            ticket.classification.reasoning,
            ticket.support_line,
            ticket.status.value,
            ticket.created_at,
            ticket.updated_at,
            ticket.rag_answer,
            json.dumps(ticket.conversation_history or [], ensure_ascii=False),
            ticket.resolved,
            ticket.resolution,
            ticket.resolved_at,
            json.dumps(ticket.tags or [], ensure_ascii=False),
            ticket.assigned_to,
            ticket.escalation_reason,
            ticket.user_satisfaction
        ))
        
        ticket.id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return ticket
    
    def get_ticket(self, ticket_id: int) -> Optional[Ticket]:
        """Получение тикета по ID"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_ticket(dict(row))
    
    def get_tickets_by_user(self, user_id: int, limit: int = 10) -> List[Ticket]:
        """Получение тикетов пользователя"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT * FROM tickets 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [self._row_to_ticket(dict(row)) for row in rows]
    
    def get_tickets_by_line(self, support_line: int, status: Optional[TicketStatus] = None) -> List[Ticket]:
        """Получение тикетов по линии поддержки"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if status:
            cursor.execute("""
                SELECT * FROM tickets 
                WHERE support_line = %s AND status = %s
                ORDER BY 
                    CASE priority
                        WHEN 'критическая' THEN 1
                        WHEN 'высокая' THEN 2
                        WHEN 'средняя' THEN 3
                        WHEN 'низкая' THEN 4
                    END,
                    created_at ASC
            """, (support_line, status.value))
        else:
            cursor.execute("""
                SELECT * FROM tickets 
                WHERE support_line = %s
                ORDER BY 
                    CASE priority
                        WHEN 'критическая' THEN 1
                        WHEN 'высокая' THEN 2
                        WHEN 'средняя' THEN 3
                        WHEN 'низкая' THEN 4
                    END,
                    created_at ASC
            """, (support_line,))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [self._row_to_ticket(dict(row)) for row in rows]
    
    def update_ticket(self, ticket: Ticket) -> Ticket:
        """Обновление тикета"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        ticket.updated_at = datetime.now()
        
        cursor.execute("""
            UPDATE tickets SET
                title = %s, description = %s, theme = %s, ticket_type = %s, priority = %s,
                system_service = %s, reasoning = %s, support_line = %s, status = %s,
                updated_at = %s, rag_answer = %s, conversation_history = %s,
                resolved = %s, resolution = %s, resolved_at = %s,
                tags = %s, assigned_to = %s, escalation_reason = %s, user_satisfaction = %s
            WHERE id = %s
        """, (
            ticket.title,
            ticket.description,
            ticket.classification.theme,
            ticket.classification.ticket_type.value,
            ticket.classification.priority.value,
            ticket.classification.system_service,
            ticket.classification.reasoning,
            ticket.support_line,
            ticket.status.value,
            ticket.updated_at,
            ticket.rag_answer,
            json.dumps(ticket.conversation_history or [], ensure_ascii=False),
            ticket.resolved,
            ticket.resolution,
            ticket.resolved_at,
            json.dumps(ticket.tags or [], ensure_ascii=False),
            ticket.assigned_to,
            ticket.escalation_reason,
            ticket.user_satisfaction,
            ticket.id
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return ticket
    
    def _row_to_ticket(self, data: dict) -> Ticket:
        """Преобразование строки БД в объект Ticket"""
        # Преобразуем JSON поля
        if isinstance(data.get('conversation_history'), str):
            data['conversation_history'] = json.loads(data['conversation_history'])
        elif data.get('conversation_history') is None:
            data['conversation_history'] = []
        
        if isinstance(data.get('tags'), str):
            data['tags'] = json.loads(data['tags'])
        elif data.get('tags') is None:
            data['tags'] = []
        
        # Создаем классификацию
        classification = TicketClassification(
            theme=data['theme'],
            ticket_type=TicketType(data['ticket_type']),
            priority=TicketPriority(data['priority']),
            system_service=data.get('system_service'),
            reasoning=data.get('reasoning', '')
        )
        
        # Создаем тикет
        return Ticket(
            id=data['id'],
            ticket_number=data['ticket_number'],
            user_id=data['user_id'],
            username=data.get('username', ''),
            title=data.get('title', data.get('description', '')[:100]),
            description=data['description'],
            classification=classification,
            support_line=data['support_line'],
            status=TicketStatus(data['status']),
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            rag_answer=data.get('rag_answer'),
            conversation_history=data.get('conversation_history'),
            resolved=bool(data.get('resolved', False)),
            resolution=data.get('resolution'),
            resolved_at=data.get('resolved_at'),
            tags=data.get('tags'),
            assigned_to=data.get('assigned_to'),
            escalation_reason=data.get('escalation_reason'),
            user_satisfaction=data.get('user_satisfaction')
        )
    
    def get_queue_stats(self) -> Dict:
        """Получение статистики очередей"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        for line in [1, 2, 3]:
            cursor.execute("""
                SELECT COUNT(*) FROM tickets 
                WHERE support_line = %s AND status IN ('Новое', 'В работе')
            """, (line,))
            stats[f'line_{line}_pending'] = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        return stats
