"""
Endpoints для работы с тикетами
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database import get_db, TicketRepository
from database.models import Ticket
from bot.ticket_models import TicketStatus, TicketPriority, TicketType

router = APIRouter()


class TicketResponse(BaseModel):
    id: int
    ticket_number: str
    user_id: int
    username: Optional[str]
    title: str
    description: str
    theme: str
    ticket_type: str
    priority: str
    system_service: Optional[str]
    support_line: int
    status: str
    created_at: datetime
    updated_at: datetime
    resolved: bool

    class Config:
        from_attributes = True


class TicketCreate(BaseModel):
    user_id: int
    username: Optional[str]
    title: str
    description: str
    theme: str
    ticket_type: str
    priority: str
    system_service: Optional[str]
    support_line: int


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    resolution: Optional[str] = None
    assigned_to: Optional[str] = None
    tags: Optional[List[str]] = None


@router.get("/", response_model=List[TicketResponse])
async def get_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    support_line: Optional[int] = Query(None, ge=1, le=3),
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Получение списка тикетов"""
    repo = TicketRepository(db)
    
    if user_id:
        tickets = repo.get_by_user(user_id, limit=limit)
    elif support_line:
        ticket_status = TicketStatus(status) if status else None
        tickets = repo.get_by_support_line(support_line, ticket_status)
    else:
        # Простой список всех тикетов
        query = db.query(Ticket)
        if status:
            query = query.filter(Ticket.status == status)
        if support_line:
            query = query.filter(Ticket.support_line == support_line)
        tickets = query.order_by(Ticket.created_at.desc()).offset(skip).limit(limit).all()
    
    return tickets


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """Получение тикета по ID"""
    repo = TicketRepository(db)
    ticket = repo.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.get("/number/{ticket_number}", response_model=TicketResponse)
async def get_ticket_by_number(ticket_number: str, db: Session = Depends(get_db)):
    """Получение тикета по номеру"""
    repo = TicketRepository(db)
    ticket = repo.get_by_ticket_number(ticket_number)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.post("/", response_model=TicketResponse, status_code=201)
async def create_ticket(ticket_data: TicketCreate, db: Session = Depends(get_db)):
    """Создание нового тикета"""
    from bot.ticket_models import Ticket, TicketClassification
    
    repo = TicketRepository(db)
    
    classification = TicketClassification(
        theme=ticket_data.theme,
        ticket_type=TicketType(ticket_data.ticket_type),
        priority=TicketPriority(ticket_data.priority),
        system_service=ticket_data.system_service
    )
    
    ticket = Ticket(
        user_id=ticket_data.user_id,
        username=ticket_data.username,
        title=ticket_data.title,
        description=ticket_data.description,
        classification=classification,
        support_line=ticket_data.support_line,
        status=TicketStatus.NEW,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db_ticket = repo.create(ticket)
    return db_ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: int,
    ticket_update: TicketUpdate,
    db: Session = Depends(get_db)
):
    """Обновление тикета"""
    repo = TicketRepository(db)
    ticket = repo.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Преобразуем в доменную модель
    ticket_model = repo.to_ticket_model(ticket)
    
    # Обновляем поля
    if ticket_update.status:
        ticket_model.status = TicketStatus(ticket_update.status)
    if ticket_update.resolution:
        ticket_model.resolution = ticket_update.resolution
    if ticket_update.assigned_to:
        ticket_model.assigned_to = ticket_update.assigned_to
    if ticket_update.tags:
        ticket_model.tags = ticket_update.tags
    
    updated_ticket = repo.update(ticket_model)
    return updated_ticket


@router.get("/stats/queue")
async def get_queue_stats(db: Session = Depends(get_db)):
    """Получение статистики очередей"""
    repo = TicketRepository(db)
    return repo.get_queue_stats()
