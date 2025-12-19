""" 
Система классификации входящих запросов на базе ИИ.
Определяет домен вопроса, категорию, критичность и необходимость оффлайн-визита.
"""
import json
import logging
import re
from typing import Dict, List, Optional, Any

from gigachat_client import GigaChatClient
from models import Category, Criticality, SupportLine

logger = logging.getLogger(__name__)

class RequestClassifier:
    """
    Классификатор обращений, использующий LLM для семантического анализа запроса.
    """
    
    def __init__(self, gigachat_client: GigaChatClient):
        """
        Инициализация классификатора.
        
        Args:
            gigachat_client: Экземпляр клиента GigaChat для генерации ответов.
        """
        self.gigachat_client = gigachat_client

    async def classify(self, user_message: str, conversation_history: List[dict] = None) -> Dict[str, Any]:
        """
        Анализирует сообщение пользователя в контексте истории диалога.
        
        Returns:
            Dict: Результаты классификации (category, criticality, is_bank_related и др.).
        """
        history_text = ""
        has_history = conversation_history and len(conversation_history) > 0
        if has_history:
            # Берем последние 5 сообщений для контекста
            history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-5:]])
        
        prompt = self._get_classification_prompt(user_message, history_text, has_history)
        response = await self.gigachat_client.generate_response([{"role": "user", "content": prompt}])
        
        return self._parse_json_result(response, has_history)

    def _get_classification_prompt(self, message: str, history: str, exists: bool) -> str:
        """Формирует строгий промпт для LLM классификатора."""
        return f"""Ты специалист поддержки СБЕРБАНКА. Проанализируй обращение пользователя.

КРИТЕРИИ КЛАССИФИКАЦИИ:
1. category (technical/billing/account/feature/bug/other)
2. criticality (low/medium/high/critical)
3. support_line (line_1 - простые, line_2 - технические, line_3 - сложные)
5. is_bank_related (true/false):
   - TRUE: Только классические БАНКОВСКИЕ услуги: карты, кредиты, вклады, переводы, ипотека, инвестиции, работа приложения "СберБанк Онлайн".
   - FALSE: Любые товары и услуги ЭКОСИСТЕМЫ (СберМаркет, Мегамаркет, СберТех, СберМобайл, СберПиво) или выдуманные продукты. Если вопрос про "СберПиво" - это FALSE.
6. is_new_topic (true/false) - это НОВАЯ тема или продолжение предыдущего разговора.
7. needs_offline (true/false) - требуется ли ЛИЧНЫЙ визит в офис.

{"ИСТОРИЯ РАЗГОВОРА:" if exists else "ЭТО ПЕРВОЕ СООБЩЕНИЕ (is_new_topic = true)"}
{history}

ТЕКУЩЕЕ СООБЩЕНИЕ:
{message}

Ответь ТОЛЬКО JSON:
{{
    "category": "...",
    "criticality": "...",
    "support_line": "...",
    "is_bank_related": true/false,
    "is_new_topic": {"true/false" if exists else "true"},
    "needs_offline": true/false,
    "reasoning": "краткое пояснение причины классификации"
}}"""

    def _parse_json_result(self, response: str, has_history: bool) -> Dict[str, Any]:
        """Отказоустойчивое извлечение JSON из текста ответа LLM."""
        try:
            # Очистка от "умных" кавычек и других частых ошибок LLM
            sanitized = response.replace('“', '"').replace('”', '"').replace('„', '"')
            
            # Пытаемся найти JSON блок через регулярное выражение
            json_match = re.search(r'\{.*\}', sanitized, re.DOTALL)
            if json_match:
                clean_response = json_match.group(0)
            else:
                clean_response = sanitized.strip()
            
            data = json.loads(clean_response)
            
            # Маппинг строковых значений в Enum модели
            return {
                "category": self._map_category(data.get("category")),
                "criticality": self._map_criticality(data.get("criticality")),
                "support_line": self._map_support_line(data.get("support_line")),
                "is_bank_related": bool(data.get("is_bank_related", True)),
                "is_new_topic": bool(data.get("is_new_topic", not has_history)),
                "needs_offline": bool(data.get("needs_offline", False)),
                "reasoning": data.get("reasoning", "Классификация завершена")
            }
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга JSON классификатора: {e}. Ответ: {response}")
            # Возвращаем безопасный дефолт при ошибке
            return {
                "category": Category.OTHER, "criticality": Criticality.LOW,
                "support_line": SupportLine.LINE_1, "is_bank_related": True,
                "is_new_topic": True, "needs_offline": False, "reasoning": f"Ошибка анализа: {e}"
            }

    def _map_category(self, val: str) -> Category:
        """Приведение строки к Enum Category."""
        mapping = {
            "technical": Category.TECHNICAL, "billing": Category.BILLING,
            "account": Category.ACCOUNT, "feature": Category.FEATURE,
            "bug": Category.BUG
        }
        return mapping.get(str(val).lower(), Category.OTHER)

    def _map_criticality(self, val: str) -> Criticality:
        """Приведение строки к Enum Criticality."""
        mapping = {
            "low": Criticality.LOW, "medium": Criticality.MEDIUM,
            "high": Criticality.HIGH, "critical": Criticality.CRITICAL
        }
        return mapping.get(str(val).lower(), Criticality.LOW)

    def _map_support_line(self, val: str) -> SupportLine:
        """Приведение строки к Enum SupportLine."""
        mapping = {
            "line_1": SupportLine.LINE_1, "line_2": SupportLine.LINE_2, "line_3": SupportLine.LINE_3
        }
        return mapping.get(str(val).lower(), SupportLine.LINE_1)

    async def assess_response(self, user_question: str, bot_answer: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Самооценка полезности ответа агента (Adaptive Intelligence).
        Использует динамический порог уверенности из метрик.
        """
        from metrics import metrics
        
        # Получаем текущий адаптивный порог (Autopilot)
        confidence_threshold = metrics.get_adaptive_threshold()
        
        prompt = f"""Ты эксперт контроля качества службы поддержки СБЕРБАНКА.
Оцени, насколько полезен ответ ИИ-ассистента на вопрос пользователя.

ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{user_question}

ОТВЕТ ИИ-АССИСТЕНТА:
{bot_answer}

КРИТЕРИИ ОЦЕНКИ:
1. is_resolved (true/false) - Содержит ли ответ КОНКРЕТНОЕ решение проблемы?
2. confidence (0-100) - Числовая оценка уверенности в ответе.
3. needs_escalation (true/false) - Требуется ли подключение живого специалиста?
4. escalation_reason - Если needs_escalation=true, укажи КРАТКУЮ причину

ПРАВИЛА:
- Если ответ содержит "не могу", "обратитесь", "уточните" -> needs_escalation = true
- Оценивай confidence ЧЕСТНО.
- Не пытайся скрыть неуверенность.

Ответь ТОЛЬКО JSON:
{{
    "is_resolved": true/false,
    "confidence": 0-100,
    "needs_escalation": true/false,
    "escalation_reason": "причина или null"
}}"""

        try:
            response = await self.gigachat_client.generate_response([{"role": "user", "content": prompt}])
            
            # Очистка и парсинг
            sanitized = response.replace('"', '"').replace('"', '"').replace('„', '"')
            json_match = re.search(r'\{.*\}', sanitized, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                
                confidence = int(data.get("confidence", 50))
                is_resolved = bool(data.get("is_resolved", False))
                needs_escalation = bool(data.get("needs_escalation", False))
                escalation_reason = data.get("escalation_reason")

                # --- ADAPTIVE INTELLIGENCE LOGIC ---
                # Жесткая отсечка по динамическому порогу
                if confidence < confidence_threshold and not needs_escalation:
                    needs_escalation = True
                    is_resolved = False
                    escalation_reason = f"Confidence {confidence}% < Threshold {confidence_threshold}% (Autopilot)"
                # -----------------------------------

                # Автоматическая эскалация на 2/3 линию
                support_line = classification.get("support_line", SupportLine.LINE_1)
                if support_line in [SupportLine.LINE_2, SupportLine.LINE_3]:
                    needs_escalation = True
                    escalation_reason = f"Автомаршрутизация на {support_line.value}"
                
                return {
                    "is_resolved": is_resolved,
                    "confidence": confidence,
                    "needs_escalation": needs_escalation,
                    "escalation_reason": escalation_reason
                }
        except Exception as e:
            logger.error(f"❌ Ошибка самооценки: {e}")
        
        # Безопасный дефолт
        return {
            "is_resolved": True,
            "confidence": 70,
            "needs_escalation": False,
            "escalation_reason": None
        }
