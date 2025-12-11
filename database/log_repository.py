"""
Репозиторий для работы с логами в PostgreSQL
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import datetime, timedelta
from .models import Log


class LogRepository:
    """Репозиторий для работы с логами"""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        level: str,
        message: str,
        logger_name: Optional[str] = None,
        module: Optional[str] = None,
        function_name: Optional[str] = None,
        line_number: Optional[int] = None,
        user_id: Optional[int] = None,
        ticket_id: Optional[int] = None,
        extra_data: Optional[dict] = None,
        traceback: Optional[str] = None
    ) -> Log:
        """Создание нового лога"""
        log = Log(
            timestamp=datetime.utcnow(),
            level=level,
            logger_name=logger_name,
            message=message,
            module=module,
            function_name=function_name,
            line_number=line_number,
            user_id=user_id,
            ticket_id=ticket_id,
            extra_data=extra_data,
            traceback=traceback
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_by_ticket(self, ticket_id: int, limit: int = 100) -> List[Log]:
        """Получение логов по тикету"""
        return self.db.query(Log).filter(
            Log.ticket_id == ticket_id
        ).order_by(desc(Log.timestamp)).limit(limit).all()

    def get_by_user(self, user_id: int, limit: int = 100) -> List[Log]:
        """Получение логов по пользователю"""
        return self.db.query(Log).filter(
            Log.user_id == user_id
        ).order_by(desc(Log.timestamp)).limit(limit).all()

    def get_by_level(self, level: str, hours: int = 24, limit: int = 1000) -> List[Log]:
        """Получение логов по уровню за последние N часов"""
        since = datetime.utcnow() - timedelta(hours=hours)
        return self.db.query(Log).filter(
            and_(
                Log.level == level,
                Log.timestamp >= since
            )
        ).order_by(desc(Log.timestamp)).limit(limit).all()

    def get_recent(self, hours: int = 24, limit: int = 1000) -> List[Log]:
        """Получение последних логов"""
        since = datetime.utcnow() - timedelta(hours=hours)
        return self.db.query(Log).filter(
            Log.timestamp >= since
        ).order_by(desc(Log.timestamp)).limit(limit).all()
