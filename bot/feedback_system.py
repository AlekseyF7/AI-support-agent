"""
Система обратной связи и определения успешности решения (PB5)
"""
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import re


class FeedbackSystem:
    """Система определения успешности решения и обратной связи"""
    
    # Ключевые слова удовлетворенности
    SATISFACTION_KEYWORDS = [
        "спасибо", "благодарю", "помогло", "решило", "работает", 
        "отлично", "хорошо", "понял", "ясно", "разобрался",
        "все ок", "все хорошо", "проблема решена", "решено"
    ]
    
    # Ключевые слова неудовлетворенности
    DISSATISFACTION_KEYWORDS = [
        "не помогло", "не работает", "не решило", "не понял",
        "не ясно", "не разобрался", "все еще", "по-прежнему",
        "плохо", "не то", "неправильно", "ошибка", "не то что нужно"
    ]
    
    # Вопросы для уточнения
    CLARIFICATION_QUESTIONS = [
        "Помог ли вам ответ?",
        "Решило ли это вашу проблему?",
        "Все ли понятно?",
        "Нужна ли дополнительная помощь?",
        "Работает ли это сейчас?"
    ]
    
    def __init__(self):
        self.pending_feedback: Dict[int, Dict] = {}  # user_id -> {ticket_id, question, timestamp}
        self.feedback_timeout = timedelta(minutes=30)  # Таймаут для обратной связи
    
    def should_ask_feedback(self, user_id: int, has_good_answer: bool, is_faq: bool) -> bool:
        """
        Определяет, нужно ли спрашивать обратную связь
        
        Args:
            user_id: ID пользователя
            has_good_answer: Есть ли хороший ответ из RAG
            is_faq: Является ли это FAQ вопросом
            
        Returns:
            True если нужно спросить обратную связь
        """
        # Спрашиваем обратную связь если:
        # 1. Есть хороший ответ ИЛИ это FAQ
        # 2. Нет активного ожидания обратной связи
        if (has_good_answer or is_faq) and user_id not in self.pending_feedback:
            return True
        return False
    
    def get_feedback_question(self) -> str:
        """Получить вопрос для обратной связи"""
        import random
        return random.choice(self.CLARIFICATION_QUESTIONS)
    
    def analyze_feedback(self, user_id: int, message: str) -> Optional[str]:
        """
        Анализирует ответ пользователя на вопрос обратной связи
        
        Args:
            user_id: ID пользователя
            message: Сообщение пользователя
            
        Returns:
            "satisfied", "not_satisfied" или None если не обратная связь
        """
        message_lower = message.lower()
        
        # Проверяем ключевые слова удовлетворенности
        satisfaction_count = sum(1 for keyword in self.SATISFACTION_KEYWORDS if keyword in message_lower)
        dissatisfaction_count = sum(1 for keyword in self.DISSATISFACTION_KEYWORDS if keyword in message_lower)
        
        # Проверяем явные ответы
        if any(word in message_lower for word in ["да", "yes", "конечно", "ага", "угу"]):
            if dissatisfaction_count == 0:
                return "satisfied"
        
        if any(word in message_lower for word in ["нет", "no", "не", "неа"]):
            if satisfaction_count == 0:
                return "not_satisfied"
        
        # Анализ по ключевым словам
        if satisfaction_count > dissatisfaction_count and satisfaction_count > 0:
            return "satisfied"
        elif dissatisfaction_count > satisfaction_count and dissatisfaction_count > 0:
            return "not_satisfied"
        
        return None
    
    def should_escalate_after_feedback(self, feedback: str, ticket_type: str) -> bool:
        """
        Определяет, нужно ли эскалировать после обратной связи
        
        Args:
            feedback: Результат обратной связи ("satisfied"/"not_satisfied")
            ticket_type: Тип тикета ("консультация"/"инцидент")
            
        Returns:
            True если нужно эскалировать
        """
        # Эскалируем если:
        # 1. Пользователь не удовлетворен
        # 2. Это инцидент (проблема не решена)
        if feedback == "not_satisfied":
            return True
        if feedback == "satisfied" and ticket_type == "инцидент":
            # Для инцидентов даже при удовлетворенности может потребоваться эскалация
            return False
        return False
    
    def register_feedback_request(self, user_id: int, ticket_id: int, question: str):
        """Регистрирует запрос обратной связи"""
        self.pending_feedback[user_id] = {
            "ticket_id": ticket_id,
            "question": question,
            "timestamp": datetime.now()
        }
    
    def clear_feedback_request(self, user_id: int):
        """Очищает запрос обратной связи"""
        if user_id in self.pending_feedback:
            del self.pending_feedback[user_id]
    
    def get_pending_feedback(self, user_id: int) -> Optional[Dict]:
        """Получить активный запрос обратной связи"""
        if user_id not in self.pending_feedback:
            return None
        
        feedback = self.pending_feedback[user_id]
        # Проверяем таймаут
        if datetime.now() - feedback["timestamp"] > self.feedback_timeout:
            del self.pending_feedback[user_id]
            return None
        
        return feedback
    
    def is_feedback_message(self, user_id: int, message: str) -> bool:
        """
        Проверяет, является ли сообщение ответом на вопрос обратной связи
        """
        pending = self.get_pending_feedback(user_id)
        if not pending:
            return False
        
        # Проверяем, похоже ли сообщение на ответ на вопрос обратной связи
        message_lower = message.lower()
        
        # Короткие ответы (да/нет)
        if len(message_lower.split()) <= 3:
            if any(word in message_lower for word in ["да", "нет", "yes", "no", "конечно", "не", "ага", "неа"]):
                return True
        
        # Ответы с ключевыми словами обратной связи
        if any(keyword in message_lower for keyword in self.SATISFACTION_KEYWORDS + self.DISSATISFACTION_KEYWORDS):
            return True
        
        return False

