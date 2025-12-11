"""
Классификатор тематики и критичности обращений (PB4)
"""
import os
import time
from typing import Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import json

from .ticket_models import TicketClassification, TicketType, TicketPriority
from .utils.retry import retry_with_backoff
from .utils.cache import CacheManager
from .utils.metrics import get_metrics
from .utils.logger import get_logger

load_dotenv()

logger = get_logger(__name__)
metrics = get_metrics()


class TicketClassifier:
    """Классификатор для определения тематики, типа и критичности обращения (PB4)"""
    
    # Тематики обращений (системы/сервисы)
    THEMES = [
        "Доступ к системе",
        "Техническая проблема",
        "Программное обеспечение",
        "Оборудование",
        "Безопасность",
        "Конфигурация",
        "Системная проблема",
        "FAQ - Общие вопросы",
        "FAQ - Пароль",
        "FAQ - Антивирус",
        "Доступ к ресурсам",
        "Сетевая проблема",
    ]
    
    # Типы обращений
    TICKET_TYPES = {
        "консультация": "Вопрос, нужна помощь, инструкция",
        "инцидент": "Проблема, что-то не работает, ошибка"
    }
    
    # Уровни критичности
    PRIORITIES = {
        "P1": "критическая",
        "P2": "высокая",
        "P3": "средняя",
        "P4": "низкая"
    }
    
    # Системы/сервисы для определения
    SYSTEMS_SERVICES = [
        "Корпоративный портал",
        "Почтовый сервер",
        "База данных",
        "Сетевое хранилище",
        "Система авторизации",
        "Антивирус",
        "Принтер/Сканер",
        "Wi-Fi",
        "VPN",
        "Другое"
    ]
    
    def __init__(self):
        import os
        # Инициализация кэша
        use_redis = os.getenv("USE_REDIS", "false").lower() == "true"
        self.cache = CacheManager(use_redis=use_redis)
        
        # Определение провайдера LLM
        llm_provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        
        if llm_provider == "ollama":
            # Использование Ollama для локальных моделей
            from langchain_community.llms import Ollama
            
            ollama_model = os.getenv("OLLAMA_MODEL", "mistral")
            ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            
            # Оптимизация для скорости классификации
            self.llm = Ollama(
                model=ollama_model, 
                base_url=ollama_base_url,
                temperature=0.1,  # Низкая температура для быстрых ответов
                num_predict=256,  # Короткие ответы для классификации
            )
            print(f"[INFO] Classifier использует Ollama с моделью: {ollama_model} (оптимизировано для скорости)")
        else:
            # Использование OpenAI
            openai_kwargs = {}
            if os.getenv("OPENAI_PROXY"):
                import httpx
                proxy_url = os.getenv("OPENAI_PROXY")
                openai_kwargs["http_client"] = httpx.Client(proxies=proxy_url, timeout=60.0)
            if os.getenv("OPENAI_BASE_URL"):
                openai_kwargs["base_url"] = os.getenv("OPENAI_BASE_URL")
            
            self.llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", **openai_kwargs)
            print(f"[INFO] Classifier использует OpenAI")
        
        # Промпт для классификации (PB4: расширенная схема меток)
        self.classification_prompt = ChatPromptTemplate.from_messages([
            ("system", """Ты - эксперт по классификации IT-обращений. Отвечай ТОЛЬКО на русском языке.

ВАЖНО: Классифицируй ТОЛЬКО обращения, связанные с технической поддержкой (IT, программы, доступ, оборудование).
Если обращение НЕ о техподдержке - верни priority: "P4", theme: "FAQ - Общие вопросы", ticket_type: "консультация".

Определи:
1. Тематику (система/сервис)
2. Тип обращения (консультация/инцидент)
3. Критичность (низкая/средняя/высокая/критическая)
4. Конкретную систему/сервис (если возможно)

Тематики: {themes}

Типы обращений:
- консультация: Вопрос, нужна помощь, инструкция, "как сделать"
- инцидент: Проблема, что-то не работает, ошибка, "не могу", "не работает"

Критичность:
- критическая (P1): Полная недоступность системы, утечка данных, критический сбой
- высокая (P2): Недоступность для группы пользователей, серьезная проблема
- средняя (P3): Проблемы с функциями, частичная недоступность
- низкая (P4): Мелкие ошибки, FAQ, общие вопросы

Системы/сервисы: {systems}

Верни ТОЛЬКО JSON на русском:
{{
    "theme": "название тематики",
    "ticket_type": "консультация" или "инцидент",
    "priority": "P1/P2/P3/P4",
    "system_service": "конкретная система/сервис или null",
    "reasoning": "краткое обоснование на русском"
}}"""),
            ("human", "Описание: {description}")
        ])
    
    def classify(self, description: str, conversation_history: List[str] = None) -> TicketClassification:
        """
        Классифицирует обращение (PB4: расширенная классификация) с кэшированием и retry
        
        Args:
            description: Описание проблемы от пользователя
            conversation_history: История диалога (опционально)
            
        Returns:
            TicketClassification с полями:
                - theme: тематика (система/сервис)
                - ticket_type: тип (консультация/инцидент)
                - priority: критичность (низкая/средняя/высокая/критическая)
                - system_service: конкретная система/сервис
                - reasoning: обоснование
        """
        # Добавляем контекст из истории диалога если есть
        full_description = description
        if conversation_history:
            context = "\n".join(conversation_history[-3:])  # Последние 3 сообщения
            full_description = f"Контекст диалога:\n{context}\n\nТекущее обращение: {description}"
        
        # Проверка кэша
        cache_key = self.cache._make_key("classification", full_description)
        cached_result = self.cache.get(cache_key)
        if cached_result:
            logger.debug(f"Кэш попадание для классификации: {description[:50]}")
            metrics.increment("classification_cache_hit")
            return cached_result
        
        metrics.increment("classification_cache_miss")
        
        start_time = time.time()
        try:
            # Используем retry для классификации
            result = self._classify_with_retry(full_description)
            
            # Сохраняем в кэш
            self.cache.set(cache_key, result, ttl=1800)  # Кэш на 30 минут
            
            # Записываем метрики
            duration = time.time() - start_time
            metrics.record_timing("classification_time", duration)
            metrics.increment("classifications_total")
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            metrics.record_timing("classification_time", duration)
            metrics.increment("classifications_errors")
            raise
    
    @retry_with_backoff(max_retries=3, initial_delay=1.0, exceptions=(Exception,))
    def _classify_with_retry(self, full_description: str) -> TicketClassification:
        """Внутренний метод для классификации с retry"""
        try:
            themes_str = "\n".join([f"- {theme}" for theme in self.THEMES])
            systems_str = "\n".join([f"- {system}" for system in self.SYSTEMS_SERVICES])
            
            # Для Ollama используем прямой промпт
            prompt_text = self.classification_prompt.format(
                themes=themes_str,
                systems=systems_str,
                description=full_description
            )
            content = self.llm.invoke(prompt_text)
            
            # Если вернулся объект AIMessage - извлекаем content
            if hasattr(content, 'content'):
                content = content.content
            content = str(content).strip()
            
            # Парсинг JSON ответа
            # Убираем markdown код блоки если есть
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            result = json.loads(content)
            
            # Валидация и преобразование результата
            theme = result.get("theme", "Техническая проблема")
            if theme not in self.THEMES:
                theme = "Техническая проблема"
            
            ticket_type_str = result.get("ticket_type", "консультация")
            if ticket_type_str not in self.TICKET_TYPES:
                ticket_type_str = "консультация"
            ticket_type = TicketType(ticket_type_str)
            
            priority_str = result.get("priority", "P3")
            if priority_str not in self.PRIORITIES:
                priority_str = "P3"
            priority_value = self.PRIORITIES[priority_str]
            priority = TicketPriority(priority_value)
            
            system_service = result.get("system_service")
            if system_service and system_service not in self.SYSTEMS_SERVICES:
                system_service = None
            
            return TicketClassification(
                theme=theme,
                ticket_type=ticket_type,
                priority=priority,
                system_service=system_service,
                reasoning=result.get("reasoning", "Автоматическая классификация")
            )
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            logger.debug(f"Ответ модели: {content if 'content' in dir() else 'N/A'}")
            metrics.increment("classification_json_errors")
            return TicketClassification(
                theme="Техническая проблема",
                ticket_type=TicketType.CONSULTATION,
                priority=TicketPriority.MEDIUM,
                reasoning="Ошибка при классификации, использованы значения по умолчанию"
            )
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Ошибка классификации: {e}", exc_info=True)
            
            # Обработка ошибки недостаточной квоты
            if "429" in error_msg or "insufficient_quota" in error_msg.lower():
                logger.warning("ВНИМАНИЕ: Закончился баланс OpenAI. Пополните баланс на https://platform.openai.com/account/billing")
                metrics.increment("classification_quota_errors")
            
            metrics.increment("classification_errors")
            raise  # Пробрасываем исключение для retry

