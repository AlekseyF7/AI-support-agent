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
        Классификация обращения по категории, критичности и определение новой темы
        
        Args:
            user_message: Сообщение пользователя
            conversation_history: История предыдущих сообщений
        
        Returns:
            Словарь с category, criticality, support_line, is_bank_related, is_new_topic
        """
        history_text = ""
        has_history = conversation_history and len(conversation_history) > 0
        if has_history:
            history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-5:]])
        
        prompt = f"""Ты специалист поддержки СБЕРБАНКА. Проанализируй обращение пользователя.

ОПРЕДЕЛИ:
1. category (technical/billing/account/feature/bug/other)
2. criticality (low/medium/high/critical)
3. support_line (line_1 - простые, line_2 - технические, line_3 - сложные)
4. is_bank_related (true/false) - относится ли к банковской тематике Сбербанка
5. is_new_topic (true/false) - это НОВАЯ тема или продолжение предыдущего разговора

БАНКОВСКАЯ ТЕМАТИКА (is_bank_related = true):
- Сбербанк Онлайн, СберБанк, карты, счета, переводы
- Кредиты, вклады, ипотека, автоплатежи
- Блокировка карты, восстановление доступа
- Банкоматы, отделения, техподдержка банка

НЕ БАНКОВСКАЯ ТЕМАТИКА (is_bank_related = false):
- Общие вопросы, не связанные с банком
- Другие сервисы, ремонт техники, доставка

ОПРЕДЕЛЕНИЕ НОВОЙ ТЕМЫ (is_new_topic):
- true: первое сообщение, новый вопрос, смена темы
- false: уточнение, продолжение, "спасибо", "понятно"

{"ИСТОРИЯ РАЗГОВОРА:" if has_history else "ЭТО ПЕРВОЕ СООБЩЕНИЕ (is_new_topic = true)"}
{history_text}

ТЕКУЩЕЕ СООБЩЕНИЕ:
{user_message}

Ответь ТОЛЬКО JSON:
{{
    "category": "...",
    "criticality": "...",
    "support_line": "...",
    "is_bank_related": true/false,
    "is_new_topic": {"true/false" if has_history else "true"},
    "reasoning": "кратко"
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
            
            # Парсим булевы значения
            def parse_bool(value, default=True):
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "да")
                return default
            
            is_bank_related = parse_bool(result.get("is_bank_related"), True)
            is_new_topic = parse_bool(result.get("is_new_topic"), not has_history)
            
            return {
                "category": category_map.get(result.get("category", "other").lower(), Category.OTHER),
                "criticality": criticality_map.get(result.get("criticality", "low").lower(), Criticality.LOW),
                "support_line": support_line_map.get(result.get("support_line", "line_1").lower(), SupportLine.LINE_1),
                "is_bank_related": is_bank_related,
                "is_new_topic": is_new_topic,
                "reasoning": result.get("reasoning", "")
            }
        except Exception as e:
            # В случае ошибки возвращаем значения по умолчанию
            from models import Category, Criticality, SupportLine
            return {
                "category": Category.OTHER,
                "criticality": Criticality.LOW,
                "support_line": SupportLine.LINE_1,
                "is_bank_related": False,
                "is_new_topic": True,  # При ошибке считаем новой темой
                "reasoning": f"Ошибка классификации: {str(e)}"
            }

    def analyze_image_content(self, ocr_text: str) -> str:
        """
        Анализирует и очищает текст, полученный через OCR (распознавание текста с картинки).
        Убирает технический мусор, выделяет суть ошибки или интерфейса.

        Args:
            ocr_text: Сырой текст после OCR

        Returns:
            str: Краткое описание того, что изображено на скриншоте
        """
        prompt = f"""Ты - аналитик скриншотов мобильного приложения Сбербанк Онлайн.
Твоя задача: выделить суть из сырого текста распознавания (OCR) и убрать мусор.

Сырой текст OCR:
"{ocr_text}"

ИНСТРУКЦИЯ:
1. Игнорируй технические данные: время (12:00), заряд батареи (100%), названия операторов связи (MTS, Beeline).
2. Найди текст ОШИБКИ, ПРЕДУПРЕЖДЕНИЯ или название экрана (например, "Вход в приложение", "Переводы").
3. Сформулируй краткое описание (1-2 предложения) того, что видит пользователь.
4. Если текст не содержит осмысленой информации или это просто набор символов, верни "Не удалось распознать содержимое экрана".

Пример:
Вход: "12:30 4G 50% Ошибка Сервис временно недоступен Повторите попытку позже OK"
Выход: "Скриншот ошибки: Сервис временно недоступен. Предлагается повторить попытку позже."

Твой ответ:"""
        
        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = self.generate_response(messages, temperature=0.2)
            return response.strip()
        except Exception as e:
            return f"Ошибка анализа изображения: {str(e)}"
    

