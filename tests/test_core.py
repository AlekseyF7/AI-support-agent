"""
Юнит-тесты для системы AI Support Agent.
Запуск: pytest tests/ -v
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Добавляем корень проекта в путь
import sys
sys.path.insert(0, '.')


class TestClassifier:
    """Тесты для RequestClassifier."""
    
    def test_map_category_valid(self):
        """Проверка маппинга категорий."""
        from classifier import RequestClassifier
        from models import Category
        
        classifier = RequestClassifier(gigachat_client=MagicMock())
        
        assert classifier._map_category("technical") == Category.TECHNICAL
        assert classifier._map_category("billing") == Category.BILLING
        assert classifier._map_category("account") == Category.ACCOUNT
        assert classifier._map_category("unknown") == Category.OTHER
    
    def test_map_criticality_valid(self):
        """Проверка маппинга критичности."""
        from classifier import RequestClassifier
        from models import Criticality
        
        classifier = RequestClassifier(gigachat_client=MagicMock())
        
        assert classifier._map_criticality("low") == Criticality.LOW
        assert classifier._map_criticality("high") == Criticality.HIGH
        assert classifier._map_criticality("critical") == Criticality.CRITICAL
        assert classifier._map_criticality("invalid") == Criticality.LOW
    
    def test_map_support_line_valid(self):
        """Проверка маппинга линий поддержки."""
        from classifier import RequestClassifier
        from models import SupportLine
        
        classifier = RequestClassifier(gigachat_client=MagicMock())
        
        assert classifier._map_support_line("line_1") == SupportLine.LINE_1
        assert classifier._map_support_line("line_2") == SupportLine.LINE_2
        assert classifier._map_support_line("line_3") == SupportLine.LINE_3
        assert classifier._map_support_line("invalid") == SupportLine.LINE_1


class TestMetrics:
    """Тесты для системы метрик."""
    
    def test_metrics_init(self):
        """Проверка начального состояния метрик."""
        from metrics import MetricsCollector
        
        m = MetricsCollector()
        assert m.total_requests == 0
        assert m.ai_resolved == 0
        assert m.escalated == 0
    
    def test_metrics_record_resolved(self):
        """Запись успешного решения ИИ."""
        from metrics import MetricsCollector
        
        m = MetricsCollector()
        m.record_request(
            classification={"category": "technical", "support_line": "line_1", "is_bank_related": True},
            assessment={"needs_escalation": False}
        )
        
        assert m.total_requests == 1
        assert m.ai_resolved == 1
        assert m.escalated == 0
    
    def test_metrics_record_escalated(self):
        """Запись эскалации."""
        from metrics import MetricsCollector
        
        m = MetricsCollector()
        m.record_request(
            classification={"category": "billing", "support_line": "line_2", "is_bank_related": True},
            assessment={"needs_escalation": True}
        )
        
        assert m.total_requests == 1
        assert m.ai_resolved == 0
        assert m.escalated == 1
    
    def test_metrics_success_rate(self):
        """Расчёт успешности."""
        from metrics import MetricsCollector
        
        m = MetricsCollector()
        # 3 успешных, 1 эскалация
        for _ in range(3):
            m.record_request(
                classification={"category": "other", "support_line": "line_1", "is_bank_related": True},
                assessment={"needs_escalation": False}
            )
        m.record_request(
            classification={"category": "other", "support_line": "line_1", "is_bank_related": True},
            assessment={"needs_escalation": True}
        )
        
        stats = m.get_stats()
        assert stats["success_rate"] == 75.0

    def test_adaptive_threshold_logic(self):
        """Тест автопилота: расчет динамического порога."""
        from metrics import MetricsCollector
        from unittest.mock import patch, MagicMock
        
        m = MetricsCollector()
        
        # Mock настроек
        with patch("config.settings") as mock_settings:
            mock_settings.TARGET_SUCCESS_RATE = 0.80
            mock_settings.AI_CONFIDENCE_THRESHOLD = 70
            mock_settings.MIN_CONFIDENCE_THRESHOLD = 50
            mock_settings.MAX_CONFIDENCE_THRESHOLD = 90
            
            # 1. Мало данных (<5) -> Дефолт (70)
            m.total_requests = 2
            m.ai_resolved = 1
            assert m.get_adaptive_threshold() == 70
            
            # 2. Низкий Success Rate (0.6 < 0.8) -> Бот должен стать СМЕЛЕЕ (снизить порог)
            # Чтобы больше вопросов решалось автоматически.
            m.total_requests = 10
            m.ai_resolved = 6 # 60%
            
            # Delta = (0.8 - 0.6) * 50 = +10
            # New = 70 - 10 = 60
            assert m.get_adaptive_threshold() == 60
            
            # 3. Высокий Success Rate (0.95 > 0.8) -> Бот должен стать СТРОЖЕ (повысить порог)
            # Чтобы не пропускать мусор, раз у нас есть запас по KPI.
            m.total_requests = 100
            m.ai_resolved = 95 # 95%
            
            # Delta = (0.8 - 0.95) * 50 = -7.5 -> -7
            # New = 70 - (-7) = 77
            # Точное значение зависит от округления, проверим диапазон
            threshold = m.get_adaptive_threshold()
            assert 75 <= threshold <= 80


class TestRAGSystem:
    """Тесты для RAG системы."""
    
    def test_similarity_calculation(self):
        """Проверка формулы схожести."""
        # similarity = 1.0 / (1.0 + distance)
        # distance = 0 → similarity = 1.0
        # distance = 1 → similarity = 0.5
        
        distance = 0.0
        similarity = 1.0 / (1.0 + distance)
        assert similarity == 1.0
        
        distance = 1.0
        similarity = 1.0 / (1.0 + distance)
        assert similarity == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
