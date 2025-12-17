"""Классификатор обращений"""
from gigachat_client import GigaChatClient
from models import Category, Criticality, SupportLine
from typing import Dict, Optional


class RequestClassifier:
    """Классификатор обращений по тематике и критичности"""
    
    def __init__(self, gigachat_client: Optional[GigaChatClient] = None):
        """
        Инициализация классификатора.
        
        Args:
            gigachat_client: Существующий экземпляр GigaChatClient.
                           Если не передан, создается новый.
        """
        if gigachat_client is not None:
            self.gigachat_client = gigachat_client
        else:
            self.gigachat_client = GigaChatClient()
    
    def classify(self, user_message: str, conversation_history: list = None) -> Dict:
        """
        Классификация обращения
        
        Args:
            user_message: Сообщение пользователя
            conversation_history: История предыдущих сообщений
        
        Returns:
            Словарь с результатами классификации
        """
        return self.gigachat_client.classify_request(user_message, conversation_history)

