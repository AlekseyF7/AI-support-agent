"""
Health check endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db

router = APIRouter()


@router.get("/")
async def health_check():
    """Базовая проверка здоровья"""
    return {"status": "healthy"}


@router.get("/db")
async def db_health_check(db: Session = Depends(get_db)):
    """Проверка подключения к базе данных"""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@router.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Проверка готовности к работе"""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        return {"status": "not_ready", "error": str(e)}
