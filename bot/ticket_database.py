"""
База данных для хранения тикетов (SQLite)
"""
import sqlite3
import json
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path

from .ticket_models import Ticket, TicketStatus, TicketPriority


class TicketDatabase:
    """Класс для работы с базой данных тикетов"""
    
    def __init__(self, db_path: str = "data/tickets.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Инициализация базы данных и создание таблиц"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица тикетов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_number TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                theme TEXT NOT NULL,
                ticket_type TEXT NOT NULL,
                priority TEXT NOT NULL,
                system_service TEXT,
                reasoning TEXT,
                support_line INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                rag_answer TEXT,
                conversation_history TEXT,
                resolved INTEGER DEFAULT 0,
                resolution TEXT,
                resolved_at TEXT,
                tags TEXT,
                assigned_to TEXT,
                escalation_reason TEXT,
                user_satisfaction TEXT
            )
        """)
        
        # Индексы для быстрого поиска
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON tickets(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON tickets(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_support_line ON tickets(support_line)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_priority ON tickets(priority)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON tickets(created_at)")
        
        conn.commit()
        conn.close()
    
    def create_ticket(self, ticket: Ticket) -> Ticket:
        """Создание нового тикета"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Генерируем номер тикета если его нет
        if not ticket.ticket_number:
            last_id = cursor.execute("SELECT MAX(id) FROM tickets").fetchone()[0] or 0
            ticket.id = last_id + 1
            ticket.ticket_number = f"#{ticket.id:03d}"
        
        # Подготовка данных
        conversation_history_json = json.dumps(ticket.conversation_history or [], ensure_ascii=False)
        tags_json = json.dumps(ticket.tags or [], ensure_ascii=False)
        
        cursor.execute("""
            INSERT INTO tickets (
                ticket_number, user_id, username, title, description,
                theme, ticket_type, priority, system_service, reasoning,
                support_line, status, created_at, updated_at,
                rag_answer, conversation_history, resolved, resolution, resolved_at,
                tags, assigned_to, escalation_reason, user_satisfaction
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ticket.created_at.isoformat(),
            ticket.updated_at.isoformat(),
            ticket.rag_answer,
            conversation_history_json,
            1 if ticket.resolved else 0,
            ticket.resolution,
            ticket.resolved_at.isoformat() if ticket.resolved_at else None,
            tags_json,
            ticket.assigned_to,
            ticket.escalation_reason,
            ticket.user_satisfaction
        ))
        
        ticket.id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return ticket
    
    def get_ticket(self, ticket_id: int) -> Optional[Ticket]:
        """Получение тикета по ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_ticket(row)
    
    def get_tickets_by_user(self, user_id: int, limit: int = 10) -> List[Ticket]:
        """Получение тикетов пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM tickets 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_ticket(row) for row in rows]
    
    def get_tickets_by_line(self, support_line: int, status: Optional[TicketStatus] = None) -> List[Ticket]:
        """Получение тикетов по линии поддержки"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT * FROM tickets 
                WHERE support_line = ? AND status = ?
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
                WHERE support_line = ?
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
        conn.close()
        
        return [self._row_to_ticket(row) for row in rows]
    
    def update_ticket(self, ticket: Ticket) -> Ticket:
        """Обновление тикета"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        ticket.updated_at = datetime.now()
        
        conversation_history_json = json.dumps(ticket.conversation_history or [], ensure_ascii=False)
        tags_json = json.dumps(ticket.tags or [], ensure_ascii=False)
        
        cursor.execute("""
            UPDATE tickets SET
                title = ?, description = ?, theme = ?, ticket_type = ?, priority = ?,
                system_service = ?, reasoning = ?, support_line = ?, status = ?,
                updated_at = ?, rag_answer = ?, conversation_history = ?,
                resolved = ?, resolution = ?, resolved_at = ?,
                tags = ?, assigned_to = ?, escalation_reason = ?, user_satisfaction = ?
            WHERE id = ?
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
            ticket.updated_at.isoformat(),
            ticket.rag_answer,
            conversation_history_json,
            1 if ticket.resolved else 0,
            ticket.resolution,
            ticket.resolved_at.isoformat() if ticket.resolved_at else None,
            tags_json,
            ticket.assigned_to,
            ticket.escalation_reason,
            ticket.user_satisfaction,
            ticket.id
        ))
        
        conn.commit()
        conn.close()
        
        return ticket
    
    def _row_to_ticket(self, row: tuple) -> Ticket:
        """Преобразование строки БД в объект Ticket"""
        from .ticket_models import TicketType, TicketPriority, TicketStatus, TicketClassification
        
        # Получаем названия колонок
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(tickets)")
        columns = [col[1] for col in cursor.fetchall()]
        conn.close()
        
        # Создаем словарь из строки
        data = dict(zip(columns, row))
        
        # Преобразуем JSON поля
        if data.get('conversation_history'):
            data['conversation_history'] = json.loads(data['conversation_history'])
        if data.get('tags'):
            data['tags'] = json.loads(data['tags'])
        
        # Преобразуем datetime
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        if data.get('resolved_at'):
            data['resolved_at'] = datetime.fromisoformat(data['resolved_at'])
        
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
            resolved=bool(data.get('resolved', 0)),
            resolution=data.get('resolution'),
            resolved_at=data.get('resolved_at'),
            tags=data.get('tags'),
            assigned_to=data.get('assigned_to'),
            escalation_reason=data.get('escalation_reason'),
            user_satisfaction=data.get('user_satisfaction')
        )
    
    def get_queue_stats(self) -> Dict:
        """Получение статистики очередей"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        for line in [1, 2, 3]:
            cursor.execute("""
                SELECT COUNT(*) FROM tickets 
                WHERE support_line = ? AND status IN ('Новое', 'В работе')
            """, (line,))
            stats[f'line_{line}_pending'] = cursor.fetchone()[0]
        
        conn.close()
        return stats

