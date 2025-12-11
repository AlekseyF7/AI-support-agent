"""
Аналитика использования бота
"""
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from .database.database_factory import get_database
from .utils.metrics import get_metrics
from .utils.logger import get_logger

logger = get_logger(__name__)
metrics = get_metrics()


class Analytics:
    """Класс для сбора и анализа статистики использования бота"""
    
    def __init__(self):
        self.db = get_database()
    
    def get_daily_stats(self, days: int = 7) -> Dict:
        """
        Получить статистику за последние N дней
        
        Args:
            days: Количество дней
            
        Returns:
            Словарь со статистикой
        """
        stats = {
            'period_days': days,
            'total_messages': 0,
            'total_tickets': 0,
            'tickets_by_line': {1: 0, 2: 0, 3: 0},
            'tickets_by_priority': {},
            'tickets_by_status': {},
            'avg_response_time': 0,
            'user_count': 0,
        }
        
        # Получаем метрики
        metrics_stats = metrics.get_stats()
        stats['total_messages'] = metrics_stats.get('counters', {}).get('messages_total', 0)
        
        # Получаем статистику из БД (упрощенная версия)
        queue_stats = self.db.get_queue_stats()
        stats['tickets_by_line'] = {
            1: queue_stats.get('line_1_pending', 0),
            2: queue_stats.get('line_2_pending', 0),
            3: queue_stats.get('line_3_pending', 0),
        }
        
        # Среднее время ответа
        avg_rag_time = metrics.get_average_timing("rag_response_time")
        avg_classification_time = metrics.get_average_timing("classification_time")
        
        if avg_rag_time and avg_classification_time:
            stats['avg_response_time'] = avg_rag_time + avg_classification_time
        
        return stats
    
    def get_user_activity(self, user_id: int) -> Dict:
        """
        Получить активность пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь с активностью пользователя
        """
        user_stats = metrics.get_user_stats(user_id)
        user_tickets = self.db.get_tickets_by_user(user_id, limit=100)
        
        return {
            'user_id': user_id,
            'messages_sent': user_stats.get('message_sent', 0),
            'tickets_created': len(user_tickets),
            'tickets_by_status': self._count_tickets_by_status(user_tickets),
            'last_activity': datetime.now().isoformat(),  # Упрощенно
        }
    
    def _count_tickets_by_status(self, tickets: List) -> Dict:
        """Подсчитать тикеты по статусам"""
        status_counts = {}
        for ticket in tickets:
            status = ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status)
            status_counts[status] = status_counts.get(status, 0) + 1
        return status_counts
    
    def export_report(self, output_file: Optional[str] = None) -> str:
        """
        Экспортировать отчет в JSON
        
        Args:
            output_file: Путь к файлу для сохранения (если None, создается автоматически)
            
        Returns:
            Путь к сохраненному файлу
        """
        report = {
            'generated_at': datetime.now().isoformat(),
            'daily_stats': self.get_daily_stats(7),
            'metrics': metrics.get_stats(),
            'queue_stats': self.db.get_queue_stats(),
        }
        
        if output_file is None:
            output_dir = Path("data/reports")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"Отчет сохранен в {output_file}")
        return str(output_file)
    
    def get_top_users(self, limit: int = 10) -> List[Dict]:
        """
        Получить топ пользователей по активности
        
        Args:
            limit: Количество пользователей
            
        Returns:
            Список словарей с информацией о пользователях
        """
        # Упрощенная реализация - в реальности нужен запрос к БД
        # Здесь используем метрики
        all_stats = metrics.get_stats()
        # В реальной реализации нужно хранить статистику по пользователям в БД
        return []


# Глобальный экземпляр аналитики
_analytics: Optional[Analytics] = None


def get_analytics() -> Analytics:
    """Получить глобальный экземпляр аналитики"""
    global _analytics
    if _analytics is None:
        _analytics = Analytics()
    return _analytics
