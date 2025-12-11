"""
FastAPI приложение
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from prometheus_client import make_asgi_app, Counter, Histogram, Gauge
import time

from database import get_db, Base, engine
from api.routers import tickets, logs, health, metrics
from utils.logging import setup_logging, get_logger

# Инициализация логирования
setup_logging()
logger = get_logger(__name__)

# Создание таблиц
Base.metadata.create_all(bind=engine)

# Создание FastAPI приложения
app = FastAPI(
    title="AI Support Agent API",
    description="API для управления тикетами и логами",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus метрики
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Метрики приложения
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

active_tickets = Gauge(
    'active_tickets_total',
    'Total active tickets',
    ['support_line', 'status']
)

# Middleware для метрик
@app.middleware("http")
async def metrics_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response

# Подключение роутеров
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(tickets.router, prefix="/api/v1/tickets", tags=["tickets"])
app.include_router(logs.router, prefix="/api/v1/logs", tags=["logs"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["metrics"])


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "message": "AI Support Agent API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Глобальный обработчик исключений"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
