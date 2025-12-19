""" 
API Сервер для Telegram Mini App (O2O Экосистема).
Предоставляет эндпоинты для веб-интерфейса карты и раздает фронтенд.
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import List, Dict, Any

import uvicorn
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from geo_service import GeoService
from config import settings

# Логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Синглтон сервиса
geo_service = GeoService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения.
    Гарантирует закрытие HTTP соединений при выключении сервера.
    """
    logger.info("🚀 Сервер Mini App запущен")
    yield
    await geo_service.close()
    logger.info("🛑 Сервер Mini App остановлен")

app = FastAPI(
    title="Sber Support O2O API",
    description="Backend для обслуживания Telegram Mini App",
    version="1.1.0",
    lifespan=lifespan
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # В продакшене ограничить конкретным доменом
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/health", tags=["System"])
async def health_check():
    """Проверка доступности API."""
    return {"status": "ok", "service": "O2O API"}

@app.get("/api/branches", response_model=List[Dict[str, Any]], tags=["Business"])
async def get_branches(
    lat: float = Query(..., description="Широта (latitude)"),
    lon: float = Query(..., description="Долгота (longitude)"),
    radius: int = Query(5000, description="Радиус поиска в метрах")
):
    """
    Возвращает список ближайших отделений Сбербанка.
    Использует 2GIS Places API для получения актуальных данных.
    """
    try:
        branches = await geo_service.find_nearest_branches(lat, lon, radius)
        return branches
    except Exception as e:
        logger.error(f"❌ Ошибка эндпоинта /api/branches: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервиса поиска")

# Подключение фронтенда Mini App
webapp_path = os.path.join(os.path.dirname(__file__), "webapp")
if os.path.exists(webapp_path):
    # Раздаем статические файлы, включая index.html как корень
    app.mount("/", StaticFiles(directory=webapp_path, html=True), name="static")
else:
    logger.error(f"❌ Директория с фронтендом не найдена по пути: {webapp_path}")

if __name__ == "__main__":
    # Запуск сервера
    uvicorn.run("app_server:app", host="0.0.0.0", port=8000, reload=False)
