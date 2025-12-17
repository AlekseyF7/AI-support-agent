"""Клиент для работы с Giga Chat API"""
import os
import base64
import logging
import json
from typing import Optional, List, Dict

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from config import settings

logger = logging.getLogger(__name__)


class GigaChatClient:
    """Клиент для взаимодействия с Giga Chat API"""
    
    def __init__(self):
        """Инициализация клиента GigaChat с учетными данными из настроек."""
        try:
            credentials = None
            
            # Приоритет 1: если есть готовый Authorization Key
            if settings.GIGACHAT_AUTHORIZATION_KEY and settings.GIGACHAT_AUTHORIZATION_KEY.strip():
                credentials = settings.GIGACHAT_AUTHORIZATION_KEY.strip()
                logger.info("Используется GIGACHAT_AUTHORIZATION_KEY")
            
            # Приоритет 2: Client Secret (проверяем, является ли он уже base64)
            elif settings.GIGACHAT_CLIENT_SECRET and settings.GIGACHAT_CLIENT_SECRET.strip():
                secret = settings.GIGACHAT_CLIENT_SECRET.strip()
                
                # Если secret выглядит как base64 (содержит = в конце или длинный без спецсимволов)
                # то это уже готовый Authorization Key от Сбера
                if '==' in secret or (len(secret) > 50 and ':' not in secret):
                    credentials = secret
                    logger.info("GIGACHAT_CLIENT_SECRET используется как готовый Authorization Key")
                else:
                    # Формируем base64(client_id:client_secret)
                    client_id = settings.GIGACHAT_CLIENT_ID.strip() if settings.GIGACHAT_CLIENT_ID else ""
                    if client_id and client_id != "your_client_id_here":
                        creds_string = f"{client_id}:{secret}"
                    else:
                        creds_string = f":{secret}"
                    credentials = base64.b64encode(creds_string.encode('utf-8')).decode('utf-8')
                    logger.info("Используется закодированный client_id:client_secret")
            else:
                raise ValueError("Необходимо указать GIGACHAT_AUTHORIZATION_KEY или GIGACHAT_CLIENT_SECRET в .env файле")
            
            self.client = GigaChat(
                credentials=credentials,
                scope=settings.GIGACHAT_SCOPE,
                verify_ssl_certs=False
            )
            logger.info("GigaChat клиент успешно инициализирован")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Ошибка инициализации GigaChat: {error_msg}", exc_info=True)
            raise Exception(f"Не удалось инициализировать GigaChat клиент. Ошибка: {error_msg}")
    
    def generate_response(self, messages: list, temperature: float = 0.7) -> str:
        """
        Генерация ответа на основе истории сообщений
        
        Args:
            messages: Список сообщений в формате [{"role": "user", "content": "..."}, ...]
            temperature: Температура генерации (0-1) - не используется, оставлено для совместимости
        
        Returns:
            Ответ от модели
        """
        if not self.client:
            return "GigaChat клиент не инициализирован. Проверьте настройки GIGACHAT_CLIENT_SECRET в .env"
        
        try:
            # Преобразуем сообщения в формат GigaChat
            chat_messages = []
            system_content = None
            
            for msg in messages:
                if msg["role"] == "system":
                    system_content = msg["content"]
                elif msg["role"] == "user":
                    content = msg["content"]
                    if system_content:
                        # Объединяем system промпт с первым user сообщением
                        content = f"{system_content}\n\n{content}"
                        system_content = None
                    chat_messages.append(Messages(role=MessagesRole.USER, content=content))
                elif msg["role"] == "assistant":
                    chat_messages.append(Messages(role=MessagesRole.ASSISTANT, content=msg["content"]))
            
            response = self.client.chat(
                Chat(messages=chat_messages)
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа GigaChat: {e}", exc_info=True)
            return f"Извините, произошла ошибка при генерации ответа. Пожалуйста, попробуйте позже."
    
    def classify_request(self, user_message: str, conversation_history: list = None) -> dict:
        """
        Классификация обращения по категории и критичности
        
        Args:
            user_message: Сообщение пользователя
            conversation_history: История предыдущих сообщений
        
        Returns:
            Словарь с category, criticality, support_line
        """
        history_text = ""
        if conversation_history:
            history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-5:]])
        
        prompt = f"""Ты специалист по классификации обращений в службу поддержки БАНКА. 
Проанализируй следующее обращение пользователя и определи:
1. Категорию обращения (technical, billing, account, feature, bug, other)
2. Критичность (low, medium, high, critical)
3. Необходимую линию поддержки (line_1 - типовые вопросы, line_2 - технические, line_3 - сложные/критичные)
4. Относится ли вопрос к банковской тематике (is_bank_related: true/false)

ВАЖНО: Вопрос должен относиться к банковской тематике:
- Банковские услуги, счета, карты, переводы, кредиты, депозиты
- Мобильное приложение банка, интернет-банк, банкоматы
- Платежи, операции по счетам, выписки
- Банковские продукты и услуги

Если вопрос НЕ относится к банковской тематике (например, ремонт техники, общие вопросы, другие услуги), установи is_bank_related = false.

История общения (если есть):
{history_text}

Текущее обращение:
{user_message}

Ответь ТОЛЬКО в формате JSON:
{{
    "category": "категория",
    "criticality": "критичность",
    "support_line": "линия поддержки",
    "is_bank_related": true/false,
    "reasoning": "краткое обоснование"
}}"""

        messages = [{"role": "user", "content": prompt}]
        response = self.generate_response(messages, temperature=0.3)
        
        # Парсим JSON ответ
        try:
            # Извлекаем JSON из ответа, если он обернут в markdown
            response = response.strip()
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response)
            
            # Валидация и приведение к enum значениям
            from models import Category, Criticality, SupportLine
            
            category_map = {
                "technical": Category.TECHNICAL,
                "billing": Category.BILLING,
                "account": Category.ACCOUNT,
                "feature": Category.FEATURE,
                "bug": Category.BUG,
                "other": Category.OTHER
            }
            
            criticality_map = {
                "low": Criticality.LOW,
                "medium": Criticality.MEDIUM,
                "high": Criticality.HIGH,
                "critical": Criticality.CRITICAL
            }
            
            support_line_map = {
                "line_1": SupportLine.LINE_1,
                "line_2": SupportLine.LINE_2,
                "line_3": SupportLine.LINE_3
            }
            
            # Проверяем, относится ли вопрос к банковской тематике
            is_bank_related = result.get("is_bank_related", True)  # По умолчанию true для обратной совместимости
            if isinstance(is_bank_related, str):
                is_bank_related = is_bank_related.lower() in ("true", "1", "yes", "да")
            
            return {
                "category": category_map.get(result.get("category", "other").lower(), Category.OTHER),
                "criticality": criticality_map.get(result.get("criticality", "low").lower(), Criticality.LOW),
                "support_line": support_line_map.get(result.get("support_line", "line_1").lower(), SupportLine.LINE_1),
                "is_bank_related": bool(is_bank_related),
                "reasoning": result.get("reasoning", "")
            }
        except Exception as e:
            # В случае ошибки возвращаем значения по умолчанию
            from models import Category, Criticality, SupportLine
            return {
                "category": Category.OTHER,
                "criticality": Criticality.LOW,
                "support_line": SupportLine.LINE_1,
                "is_bank_related": False,  # При ошибке считаем, что не относится к банку
                "reasoning": f"Ошибка классификации: {str(e)}"
            }
    

