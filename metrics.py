"""
Система сбора метрик для анализа эффективности ИИ-агента.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class MetricsCollector:
    """Сборщик метрик работы бота."""
    
    # Счётчики
    total_requests: int = 0
    ai_resolved: int = 0  # ИИ решил сам
    escalated: int = 0    # Передано оператору
    off_topic: int = 0    # Отклонено как оффтоп
    
    # По категориям
    by_category: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_line: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Время работы
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def record_request(self, classification: Dict[str, Any], assessment: Dict[str, Any]) -> None:
        """Записывает метрики обработанного запроса."""
        self.total_requests += 1
        
        # Категория
        category = classification.get("category")
        if hasattr(category, "value"):
            category = category.value
        self.by_category[str(category)] += 1
        
        # Линия поддержки
        line = classification.get("support_line")
        if hasattr(line, "value"):
            line = line.value
        self.by_line[str(line)] += 1
        
        # Результат
        if not classification.get("is_bank_related", True):
            self.off_topic += 1
        elif assessment.get("needs_escalation"):
            self.escalated += 1
        else:
            self.ai_resolved += 1
    
    
    def get_adaptive_threshold(self) -> int:
        """
        Рассчитывает динамический порог уверенности (Autopilot).
        Цель: Удерживать Success Rate около TARGET_SUCCESS_RATE.
        """
        from config import settings
        
        # Если данных мало, возвращаем дефолт
        if self.total_requests < 5:
            return settings.AI_CONFIDENCE_THRESHOLD
            
        current_rate = self.ai_resolved / self.total_requests
        target_rate = settings.TARGET_SUCCESS_RATE
        
        # Базовый порог
        current_threshold = settings.AI_CONFIDENCE_THRESHOLD
        
        # Корректировка: 
        # Если Rate < Target (60% < 80%) -> Бот слишком строг? НЕТ.
        # Если Rate < Target -> Бот часто сваливается в эскалацию.
        # Чтобы повысить Rate (автоматизацию), нужно СНИЗИТЬ порог (быть смелее).
        # ДЕЛЬТА: (Target - Current) * Factor
        
        delta = (target_rate - current_rate) * 50  # Коэффициент "агрессивности"
        
        # Инверсия: Чтобы Rate РОС, порог должен ПАДАТЬ.
        new_threshold = current_threshold - int(delta)
        
        # Клампинг (ограничение)
        final_threshold = max(
            settings.MIN_CONFIDENCE_THRESHOLD, 
            min(new_threshold, settings.MAX_CONFIDENCE_THRESHOLD)
        )
        
        return final_threshold

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает сводку метрик."""
        uptime = datetime.now(timezone.utc) - self.started_at
        success_rate = (self.ai_resolved / self.total_requests * 100) if self.total_requests > 0 else 0
        
        return {
            "total_requests": self.total_requests,
            "ai_resolved": self.ai_resolved,
            "escalated": self.escalated,
            "off_topic": self.off_topic,
            "success_rate": round(success_rate, 1),
            "adaptive_threshold": self.get_adaptive_threshold(),  # Добавляем в отчет
            "by_category": dict(self.by_category),
            "by_line": dict(self.by_line),
            "uptime_hours": round(uptime.total_seconds() / 3600, 1)
        }
    
    def format_stats(self) -> str:
        """Форматирует метрики для отображения."""
        stats = self.get_stats()
        
        text = (
            f"📊 <b>Метрики ИИ-агента</b>\n\n"
            f"📈 Всего запросов: <b>{stats['total_requests']}</b>\n"
            f"✅ Решено ИИ: <b>{stats['ai_resolved']}</b>\n"
            f"📋 Эскалировано: <b>{stats['escalated']}</b>\n"
            f"🚫 Оффтоп: <b>{stats['off_topic']}</b>\n\n"
            f"🎯 <b>Успешность ИИ: {stats['success_rate']}%</b>\n\n"
            f"⏱ Аптайм: {stats['uptime_hours']} ч."
        )
        
        if stats['by_category']:
            text += "\n\n📂 <b>По категориям:</b>\n"
            for cat, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
                text += f"  • {cat}: {count}\n"
        
        return text


# Глобальный сборщик метрик
metrics = MetricsCollector()
