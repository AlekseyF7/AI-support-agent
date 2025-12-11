"""
Endpoints для работы с логами
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database import get_db, LogRepository

router = APIRouter()


class LogResponse(BaseModel):
    id: int
    timestamp: datetime
    level: str
    logger_name: Optional[str]
    message: str
    module: Optional[str]
    function_name: Optional[str]
    line_number: Optional[int]
    user_id: Optional[int]
    ticket_id: Optional[int]

    class Config:
        from_attributes = True


class LogCreate(BaseModel):
    level: str
    message: str
    logger_name: Optional[str] = None
    module: Optional[str] = None
    function_name: Optional[str] = None
    line_number: Optional[int] = None
    user_id: Optional[int] = None
    ticket_id: Optional[int] = None
    extra_data: Optional[dict] = None


@router.get("/", response_model=List[LogResponse])
async def get_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = None,
    ticket_id: Optional[int] = None,
    user_id: Optional[int] = None,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """Получение логов"""
    repo = LogRepository(db)
    
    if ticket_id:
        logs = repo.get_by_ticket(ticket_id, limit=limit)
    elif user_id:
        logs = repo.get_by_user(user_id, limit=limit)
    elif level:
        logs = repo.get_by_level(level, hours=hours, limit=limit)
    else:
        logs = repo.get_recent(hours=hours, limit=limit)
    
    return logs[skip:skip+limit]


@router.post("/", response_model=LogResponse, status_code=201)
async def create_log(log_data: LogCreate, db: Session = Depends(get_db)):
    """Создание нового лога"""
    repo = LogRepository(db)
    log = repo.create(
        level=log_data.level,
        message=log_data.message,
        logger_name=log_data.logger_name,
        module=log_data.module,
        function_name=log_data.function_name,
        line_number=log_data.line_number,
        user_id=log_data.user_id,
        ticket_id=log_data.ticket_id,
        extra_data=log_data.extra_data
    )
    return log


@router.get("/ticket/{ticket_id}", response_model=List[LogResponse])
async def get_ticket_logs(
    ticket_id: int,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Получение логов по тикету"""
    repo = LogRepository(db)
    logs = repo.get_by_ticket(ticket_id, limit=limit)
    return logs
