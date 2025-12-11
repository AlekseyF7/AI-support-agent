"""
Endpoints для метрик
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from database.models import Ticket, Log

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Получение метрик для дашборда"""
    # Статистика тикетов
    total_tickets = db.query(func.count(Ticket.id)).scalar()
    open_tickets = db.query(func.count(Ticket.id)).filter(
        Ticket.status.in_(['Новое', 'В работе'])
    ).scalar()
    resolved_tickets = db.query(func.count(Ticket.id)).filter(
        Ticket.status == 'Решено'
    ).scalar()
    
    # Статистика по линиям поддержки
    line_stats = {}
    for line in [1, 2, 3]:
        line_stats[f"line_{line}"] = {
            "total": db.query(func.count(Ticket.id)).filter(
                Ticket.support_line == line
            ).scalar(),
            "pending": db.query(func.count(Ticket.id)).filter(
                Ticket.support_line == line,
                Ticket.status.in_(['Новое', 'В работе'])
            ).scalar()
        }
    
    # Статистика логов
    total_logs = db.query(func.count(Log.id)).scalar()
    error_logs = db.query(func.count(Log.id)).filter(
        Log.level == 'ERROR'
    ).scalar()
    
    return {
        "tickets": {
            "total": total_tickets or 0,
            "open": open_tickets or 0,
            "resolved": resolved_tickets or 0,
            "by_line": line_stats
        },
        "logs": {
            "total": total_logs or 0,
            "errors": error_logs or 0
        }
    }
