""" 
Высокоуровневый асинхронный клиент для взаимодействия с GigaChat API.
Обеспечивает поддержку генерации текста, эмбеддингов и анализа изображений.
"""
import base64
import logging
import asyncio
from typing import List, Dict, Any, Optional

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from config import settings

logger = logging.getLogger(__name__)

class GigaChatClient:
    """
    Адаптер для SDK GigaChat с поддержкой асинхронности через thread pool executor.
    Позволяет интегрировать синхронный SDK в асинхронное приложение без блокировок.
    """
    
    def __init__(self):
        """Инициализирует SDK GigaChat используя учетные данные из настроек."""
        try:
            credentials = self._prepare_credentials()
            self.client = GigaChat(
                credentials=credentials,
                scope=settings.GIGACHAT_SCOPE,
                verify_ssl_certs=False  # Для работы через корпоративные прокси Сбера
            )
            self._semaphore = asyncio.Semaphore(1)
            logger.info("🚀 GigaChat клиент успешно инициализирован (Queue Limit: 1)")
        except Exception as e:
            logger.error(f"❌ Критическая ошибка при инициализации GigaChat: {e}")
            raise

    def _prepare_credentials(self) -> str:
        """Подготавливает строку авторизации (Base64 или Client Secret)."""
        if settings.GIGACHAT_AUTHORIZATION_KEY:
            return settings.GIGACHAT_AUTHORIZATION_KEY.strip()
        
        secret = settings.GIGACHAT_CLIENT_SECRET.strip()
        # Проверка, является ли секрет уже готовым ключом
        if '==' in secret or (len(secret) > 50 and ':' not in secret):
            return secret
        
        client_id = settings.GIGACHAT_CLIENT_ID.strip() if settings.GIGACHAT_CLIENT_ID else ""
        creds_string = f"{client_id}:{secret}"
        return base64.b64encode(creds_string.encode('utf-8')).decode('utf-8')

    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """
        Генерирует текстовый ответ на основе истории сообщений.
        
        Args:
            messages: Список словарей с ключами 'role' и 'content'.
            
        Returns:
            Текст ответа от ИИ.
        """
        async with self._semaphore:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._generate_response_sync, messages)

    def _generate_response_sync(self, messages: List[Dict[str, str]]) -> str:
        """Синхронная реализация генерации для запуска в экзекуторе."""
        try:
            chat_messages = []
            system_content = None
            
            # Конвертация в формат моделей GigaChat SDK
            for msg in messages:
                role = msg.get("role")
                content = msg.get("content", "")
                
                if role == "system":
                    system_content = content
                elif role == "user":
                    if system_content:
                        # GigaChat иногда лучше понимает, если системный промпт инжектирован в первый юзер-месседж
                        content = f"{system_content}\n\n{content}"
                        system_content = None
                    chat_messages.append(Messages(role=MessagesRole.USER, content=content))
                elif role == "assistant":
                    chat_messages.append(Messages(role=MessagesRole.ASSISTANT, content=content))
            
            response = self.client.chat(Chat(messages=chat_messages))
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"⚠️ Ошибка обращения к GigaChat API: {e}")
            return "Извините, сейчас я не могу обработать ваш запрос. Пожалуйста, попробуйте позже."

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Получает векторные представления для списка текстов.
        """
        async with self._semaphore:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._get_embeddings_sync, texts)

    def _get_embeddings_sync(self, texts: List[str]) -> List[List[float]]:
        """Синхронная генерация эмбеддингов."""
        try:
            response = self.client.embeddings(texts=texts)
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"⚠️ Ошибка получения эмбеддингов: {e}")
            return []

    async def analyze_image(self, image_data: bytes, prompt: str) -> str:
        """
        Анализирует изображение и отвечает на текстовый промпт.
        
        Args:
            image_data: Бинарные данные изображения.
            prompt: Инструкция для анализа.
        """
        async with self._semaphore:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._analyze_image_sync, image_data, prompt)

    def _analyze_image_sync(self, image_data: bytes, prompt: str) -> str:
        """Синхронный Vision анализ через предварительную загрузку файла."""
        import io
        try:
            # 1. Загрузка файла в облако GigaChat
            # SDK требует file-like object, а не сырые байты
            logger.info("📡 Загрузка изображения в GigaChat...")
            file_stream = io.BytesIO(image_data)
            file_stream.name = "image.jpg"  # SDK использует расширение для MIME-типа
            uploaded_file = self.client.upload_file(file_stream)
            logger.info(f"DEBUG: Upload response type: {type(uploaded_file)}, content: {uploaded_file}")
            
            # Попытка получить ID разными способами (SDK может меняться)
            file_id = getattr(uploaded_file, 'id', None) or getattr(uploaded_file, 'id_', None)
            
            if not file_id:
                 raise ValueError(f"Не удалось получить ID загруженного файла. Объект: {uploaded_file}")
            
            # 2. Формирование запроса с прикрепленным файлом
            logger.info(f"👁️ Анализ изображения с ID: {file_id}")
            payload = Chat(
                messages=[
                    Messages(
                        role=MessagesRole.USER,
                        content=prompt,
                        attachments=[file_id] 
                    )
                ],
                model="GigaChat-Pro",  # Модель с поддержкой Vision
                temperature=0.1,
                max_tokens=600
            )
            response = self.client.chat(payload)
            
            if not response.choices:
                raise ValueError("Пустой ответ от GigaChat Vision API")
                
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"⚠️ Ошибка Vision анализа: {e}", exc_info=True)
            return (
                "🔒 Сервис анализа изображений временно недоступен. "
                "Опишите проблему текстом."
            )

    async def close(self):
        """Безопасное закрытие ресурсов клиента."""
        try:
            if hasattr(self.client, "close"):
                # Если SDK поддерживает контекстный менеджер или метод close
                self.client.close()
            logger.info("🛡️ Сессия GigaChat успешно закрыта")
        except Exception as e:
            logger.warning(f"Ошибка при закрытии GigaChat: {e}")
