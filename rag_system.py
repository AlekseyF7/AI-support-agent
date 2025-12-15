"""RAG система для ответов на типовые вопросы"""
import json
from typing import List, Optional
import warnings
import logging

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError as e:
    CHROMADB_AVAILABLE = False
    warnings.warn(f"ChromaDB не доступен: {e}. RAG система будет работать в упрощенном режиме.")

from config import settings


class RAGSystem:
    """Система RAG для поиска релевантных ответов"""
    
    def __init__(self):
        self.chromadb_available = CHROMADB_AVAILABLE
        self.knowledge_base = {}  # Простое хранилище для упрощенного режима
        
        if self.chromadb_available:
            try:
                # Инициализация ChromaDB
                try:
                    self.client = chromadb.PersistentClient(
                        path=settings.CHROMA_DB_PATH,
                        settings=ChromaSettings(anonymized_telemetry=False)
                    )
                except Exception as e:
                    # Попробуем без settings для новых версий
                    self.client = chromadb.PersistentClient(
                        path=settings.CHROMA_DB_PATH
                    )
                
                # Используем multilingual embedding модель
                try:
                    embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
                        model_name=settings.EMBEDDING_MODEL
                    )
                    use_embedding = True
                except Exception as e:
                    logger.warning(f"Не удалось загрузить embedding функцию: {e}")
                    logger.info("Используется встроенная функция по умолчанию")
                    embedding_func = None
                    use_embedding = False
                
                # Получаем или создаем коллекцию
                try:
                    if use_embedding:
                        self.collection = self.client.get_collection(
                            name="support_knowledge_base",
                            embedding_function=embedding_func
                        )
                    else:
                        self.collection = self.client.get_collection(
                            name="support_knowledge_base"
                        )
                except:
                    if use_embedding:
                        self.collection = self.client.create_collection(
                            name="support_knowledge_base",
                            embedding_function=embedding_func
                        )
                    else:
                        self.collection = self.client.create_collection(
                            name="support_knowledge_base"
                        )
                
                # Инициализируем базовую базу знаний
                self._initialize_knowledge_base()
                logger.info("ChromaDB успешно инициализирован")
            except Exception as e:
                logger.warning(f"Ошибка инициализации ChromaDB: {e}. Используется упрощенный режим.")
                self.chromadb_available = False
                self._initialize_simple_knowledge_base()
        else:
            self._initialize_simple_knowledge_base()
    
    def _initialize_simple_knowledge_base(self):
        """Инициализация упрощенной базы знаний (без ChromaDB)"""
        self.knowledge_base = {
            "пароль": "Для сброса пароля перейдите в раздел 'Безопасность' и нажмите 'Забыли пароль?'. На вашу почту придет ссылка для восстановления.",
            "оплата": "Оплата производится через личный кабинет в разделе 'Оплата'. Доступны карты Visa, MasterCard и электронные кошельки.",
            "контакты": "Вы можете написать нам через этот бот, отправить email на support@example.com или позвонить по телефону.",
            "ошибка": "Что делать если сервис не работает: Проверьте интернет-соединение, очистите кеш браузера и попробуйте перезагрузить страницу. Если проблема сохраняется, создайте обращение.",
            "профиль": "Как изменить данные профиля: Зайдите в настройки профиля, нажмите 'Редактировать' и внесите необходимые изменения. Не забудьте сохранить.",
        }
    
    def _initialize_knowledge_base(self):
        """Инициализация базовой базы знаний"""
        if not self.chromadb_available:
            return
        
        # Проверяем, есть ли уже документы
        if self.collection.count() == 0:
            # Добавляем типовые вопросы и ответы
            knowledge_base = [
                {
                    "id": "faq_1",
                    "text": "Как сбросить пароль? Для сброса пароля перейдите в раздел 'Безопасность' и нажмите 'Забыли пароль?'. На вашу почту придет ссылка для восстановления.",
                    "metadata": {"category": "account", "tags": ["пароль", "сброс", "восстановление"]}
                },
                {
                    "id": "faq_2",
                    "text": "Как оплатить услуги? Оплата производится через личный кабинет в разделе 'Оплата'. Доступны карты Visa, MasterCard и электронные кошельки.",
                    "metadata": {"category": "billing", "tags": ["оплата", "платеж", "карта"]}
                },
                {
                    "id": "faq_3",
                    "text": "Как связаться с техподдержкой? Вы можете написать нам через этот бот, отправить email на support@example.com или позвонить по телефону.",
                    "metadata": {"category": "other", "tags": ["контакты", "поддержка"]}
                },
                {
                    "id": "faq_4",
                    "text": "Что делать если сервис не работает? Проверьте интернет-соединение, очистите кеш браузера и попробуйте перезагрузить страницу. Если проблема сохраняется, создайте обращение.",
                    "metadata": {"category": "technical", "tags": ["ошибка", "не работает", "технические проблемы"]}
                },
                {
                    "id": "faq_5",
                    "text": "Как изменить данные профиля? Зайдите в настройки профиля, нажмите 'Редактировать' и внесите необходимые изменения. Не забудьте сохранить.",
                    "metadata": {"category": "account", "tags": ["профиль", "настройки", "редактирование"]}
                }
            ]
            
            texts = [item["text"] for item in knowledge_base]
            ids = [item["id"] for item in knowledge_base]
            # Преобразуем метаданные: списки преобразуем в строки
            metadatas = []
            for item in knowledge_base:
                meta = item["metadata"].copy()
                # Преобразуем списки в строки (ChromaDB не поддерживает списки в метаданных)
                if "tags" in meta and isinstance(meta["tags"], list):
                    meta["tags"] = ", ".join(meta["tags"])
                metadatas.append(meta)
            
            self.collection.add(
                documents=texts,
                ids=ids,
                metadatas=metadatas
            )
    
    def search(self, query: str, n_results: int = 3) -> List[dict]:
        """
        Поиск релевантных документов
        
        Args:
            query: Поисковый запрос
            n_results: Количество результатов
        
        Returns:
            Список релевантных документов с метаданными
        """
        if not self.chromadb_available:
            # Простой поиск по ключевым словам
            query_lower = query.lower()
            documents = []
            for keyword, text in self.knowledge_base.items():
                if keyword in query_lower:
                    documents.append({
                        "text": text,
                        "metadata": {"keyword": keyword},
                        "distance": None
                    })
                    if len(documents) >= n_results:
                        break
            return documents
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            documents = []
            if results['documents'] and len(results['documents'][0]) > 0:
                for i, doc in enumerate(results['documents'][0]):
                    documents.append({
                        "text": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else None
                    })
            
            return documents
        except Exception as e:
            logger.warning(f"Ошибка поиска в ChromaDB: {e}. Используется упрощенный поиск.")
            # Fallback на простой поиск
            query_lower = query.lower()
            documents = []
            for keyword, text in self.knowledge_base.items():
                if keyword in query_lower:
                    documents.append({
                        "text": text,
                        "metadata": {"keyword": keyword},
                        "distance": None
                    })
                    if len(documents) >= n_results:
                        break
            return documents
    
    def add_knowledge(self, text: str, metadata: dict, doc_id: str = None):
        """
        Добавление нового документа в базу знаний
        
        Args:
            text: Текст документа
            metadata: Метаданные документа
            doc_id: Идентификатор документа (опционально)
        """
        if not self.chromadb_available:
            # В упрощенном режиме добавляем в словарь
            import uuid
            if not doc_id:
                doc_id = str(uuid.uuid4())
            # Используем первый тег как ключ, если есть
            if metadata.get("tags") and len(metadata["tags"]) > 0:
                key = metadata["tags"][0].lower()
            else:
                key = doc_id
            self.knowledge_base[key] = text
            return
        
        try:
            import uuid
            if not doc_id:
                doc_id = str(uuid.uuid4())
            
            self.collection.add(
                documents=[text],
                ids=[doc_id],
                metadatas=[metadata]
            )
        except Exception as e:
            logger.warning(f"Ошибка добавления в ChromaDB: {e}. Добавляю в упрощенную базу.")
            if metadata.get("tags") and len(metadata["tags"]) > 0:
                key = metadata["tags"][0].lower()
            else:
                key = doc_id
            self.knowledge_base[key] = text
    
    def get_context_for_query(self, query: str, max_results: int = 3) -> str:
        """
        Получение контекста для запроса
        
        Args:
            query: Запрос пользователя
            max_results: Максимальное количество релевантных документов
        
        Returns:
            Контекст в виде строки
        """
        documents = self.search(query, n_results=max_results)
        
        if not documents:
            return "Релевантная информация не найдена."
        
        context_parts = []
        for doc in documents:
            context_parts.append(doc["text"])
        
        return "\n\n".join(context_parts)

