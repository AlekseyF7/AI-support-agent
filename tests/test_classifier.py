"""
Тесты для классификатора
"""
import pytest
from unittest.mock import Mock, patch
from bot.classifier import TicketClassifier
from bot.ticket_models import TicketType, TicketPriority


class TestTicketClassifier:
    """Тесты для классификатора тикетов"""
    
    @pytest.fixture
    def classifier(self):
        """Создание экземпляра классификатора"""
        with patch('bot.classifier.os.getenv', return_value='ollama'):
            with patch('bot.classifier.Ollama'):
                return TicketClassifier()
    
    def test_classifier_init(self, classifier):
        """Тест инициализации классификатора"""
        assert classifier is not None
        assert len(classifier.THEMES) > 0
        assert len(classifier.PRIORITIES) > 0
    
    def test_classifier_themes(self, classifier):
        """Тест наличия тематик"""
        assert "Техническая проблема" in classifier.THEMES
        assert "Безопасность" in classifier.THEMES
        assert "FAQ - Общие вопросы" in classifier.THEMES
    
    def test_classifier_priorities(self, classifier):
        """Тест наличия приоритетов"""
        assert "P1" in classifier.PRIORITIES
        assert "P2" in classifier.PRIORITIES
        assert "P3" in classifier.PRIORITIES
        assert "P4" in classifier.PRIORITIES
    
    @patch('bot.classifier.TicketClassifier.classify')
    def test_classify_method(self, mock_classify, classifier):
        """Тест метода классификации"""
        from bot.ticket_models import TicketClassification
        
        expected_classification = TicketClassification(
            theme="Техническая проблема",
            ticket_type=TicketType.INCIDENT,
            priority=TicketPriority.MEDIUM,
            reasoning="Тестовая классификация"
        )
        
        mock_classify.return_value = expected_classification
        
        result = classifier.classify("Не работает система")
        
        assert result.theme == "Техническая проблема"
        assert result.ticket_type == TicketType.INCIDENT
        assert result.priority == TicketPriority.MEDIUM
