"""
Сбор метрик для мониторинга работы бота
"""
import time
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from datetime import datetime
import json
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Сборщик метрик для мониторинга"""
    
    def __init__(self, metrics_file: Optional[str] = None):
        """
        Инициализация сборщика метрик
        
        Args:
            metrics_file: Путь к файлу для сохранения метрик (опционально)
        """
        self.metrics_file = metrics_file or os.getenv("METRICS_FILE", "data/metrics.json")
        
        # Счетчики
        self.counters: Dict[str, int] = defaultdict(int)
        
        # Временные метрики (для расчета средних значений)
        self.timings: Dict[str, List[float]] = defaultdict(list)
        
        # Метрики по пользователям
        self.user_metrics: Dict[int, Dict[str, Any]] = defaultdict(lambda: defaultdict(int))
        
        # История событий (последние N событий)
        self.events: deque = deque(maxlen=1000)
        
        # Метрики производительности
        self.performance_metrics: Dict[str, deque] = {
            'rag_response_time': deque(maxlen=100),
            'classification_time': deque(maxlen=100),
            'ticket_creation_time': deque(maxlen=100),
        }
    
    def increment(self, metric_name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """
        Увеличить счетчик метрики
        
        Args:
            metric_name: Название метрики
            value: Значение для увеличения
            labels: Дополнительные метки (для будущей поддержки Prometheus)
        """
        self.counters[metric_name] += value
        self._log_event('counter', metric_name, value, labels)
    
    def record_timing(self, metric_name: str, duration: float, labels: Optional[Dict[str, str]] = None):
        """
        Записать время выполнения
        
        Args:
            metric_name: Название метрики
            duration: Длительность в секундах
            labels: Дополнительные метки
        """
        if metric_name in self.performance_metrics:
            self.performance_metrics[metric_name].append(duration)
        
        self.timings[metric_name].append(duration)
        # Храним только последние 1000 значений
        if len(self.timings[metric_name]) > 1000:
            self.timings[metric_name] = self.timings[metric_name][-1000:]
        
        self._log_event('timing', metric_name, duration, labels)
    
    def record_user_action(self, user_id: int, action: str, value: Any = 1):
        """
        Записать действие пользователя
        
        Args:
            user_id: ID пользователя
            action: Название действия
            value: Значение
        """
        self.user_metrics[user_id][action] += value
        self.increment(f"user_{action}", value)
    
    def _log_event(self, event_type: str, metric_name: str, value: Any, labels: Optional[Dict[str, str]] = None):
        """Логирование события"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'metric': metric_name,
            'value': value,
            'labels': labels or {}
        }
        self.events.append(event)
    
    def get_counter(self, metric_name: str) -> int:
        """Получить значение счетчика"""
        return self.counters.get(metric_name, 0)
    
    def get_average_timing(self, metric_name: str) -> Optional[float]:
        """Получить среднее время выполнения"""
        timings = self.timings.get(metric_name, [])
        if not timings:
            return None
        return sum(timings) / len(timings)
    
    def get_percentile_timing(self, metric_name: str, percentile: float = 95.0) -> Optional[float]:
        """Получить перцентиль времени выполнения"""
        timings = self.timings.get(metric_name, [])
        if not timings:
            return None
        
        sorted_timings = sorted(timings)
        index = int(len(sorted_timings) * percentile / 100)
        return sorted_timings[min(index, len(sorted_timings) - 1)]
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить общую статистику"""
        stats = {
            'counters': dict(self.counters),
            'averages': {},
            'percentiles': {},
            'user_count': len(self.user_metrics),
            'total_events': len(self.events),
        }
        
        # Средние значения
        for metric_name in self.timings:
            stats['averages'][metric_name] = self.get_average_timing(metric_name)
            stats['percentiles'][metric_name] = {
                'p50': self.get_percentile_timing(metric_name, 50),
                'p95': self.get_percentile_timing(metric_name, 95),
                'p99': self.get_percentile_timing(metric_name, 99),
            }
        
        return stats
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Получить статистику по пользователю"""
        return dict(self.user_metrics.get(user_id, {}))
    
    def save_metrics(self):
        """Сохранить метрики в файл"""
        try:
            metrics_data = {
                'timestamp': datetime.now().isoformat(),
                'counters': dict(self.counters),
                'averages': {
                    name: self.get_average_timing(name)
                    for name in self.timings.keys()
                },
                'user_count': len(self.user_metrics),
                'recent_events': list(self.events)[-100],  # Последние 100 событий
            }
            
            Path(self.metrics_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(metrics_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Метрики сохранены в {self.metrics_file}")
        except Exception as e:
            logger.error(f"Ошибка сохранения метрик: {e}")
    
    def reset(self):
        """Сбросить все метрики"""
        self.counters.clear()
        self.timings.clear()
        self.user_metrics.clear()
        self.events.clear()
        for metric_list in self.performance_metrics.values():
            metric_list.clear()
    
    def export_prometheus_format(self) -> str:
        """
        Экспорт метрик в формате Prometheus
        
        Returns:
            Строка с метриками в формате Prometheus
        """
        lines = []
        
        # Счетчики
        for metric_name, value in self.counters.items():
            lines.append(f"# TYPE {metric_name} counter")
            lines.append(f"{metric_name} {value}")
        
        # Средние значения времени
        for metric_name in self.timings:
            avg = self.get_average_timing(metric_name)
            if avg is not None:
                lines.append(f"# TYPE {metric_name}_avg gauge")
                lines.append(f"{metric_name}_avg {avg}")
        
        return "\n".join(lines)


# Глобальный экземпляр сборщика метрик
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """Получить глобальный экземпляр сборщика метрик"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
