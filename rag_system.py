""" 
Система RAG (Retrieval-Augmented Generation) на базе ChromaDB и локальной модели эмбеддингов.
Обеспечивает поиск по базе знаний без затрат на API.
"""
import os
import logging
import asyncio
from typing import List, Optional, Any

import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from sentence_transformers import SentenceTransformer

from config import settings

logger = logging.getLogger(__name__)

class LocalEmbeddingFunction(EmbeddingFunction):
    """
    Адаптер для локального получения эмбеддингов через SentenceTransformer.
    Совместим с протоколом EmbeddingFunction ChromaDB.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Инициализация модели. 
        """
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        logger.info(f"🧠 Загрузка локальной модели эмбеддингов: {self.model_name}")
        try:
            self.model = SentenceTransformer(self.model_name, trust_remote_code=True)
            logger.info("✅ Модель эмбеддингов успешно загружена.")
        except Exception as e:
            logger.error(f"❌ Фатальная ошибка загрузки модели: {e}")
            raise

    def __call__(self, input: Documents) -> Embeddings:
        """
        Метод для совместимости с ChromaDB API. 
        Автоматически добавляет префикс 'passage: ' для индексируемых документов.
        """
        # Модели instruct требуют префиксов: passage для документов, query для поиска
        prefixed_texts = [f"passage: {t}" if not t.startswith("query:") else t for t in input]
        embeddings = self.model.encode(prefixed_texts)
        return embeddings.tolist()

class RAGSystem:
    """
    Система поиска по базе знаний службы поддержки.
    """
    
    def __init__(self, embedding_function: Any = None):
        """
        Инициализация RAG системы. 
        
        Args:
            embedding_function: Экземпляр функции эмбеддингов. Если None, создается локальная.
        """
        self.db_path = settings.CHROMA_DB_PATH
        self.embedding_function = embedding_function or LocalEmbeddingFunction()
        
        # Инициализация ChromaDB
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.collection = self.client.get_or_create_collection(
            name="support_knowledge_base_local",
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "l2"} # Используем L2 дистанцию
        )

    async def get_context_for_query(self, query: str, max_results: int = 3, threshold: float = 0.85) -> str:
        """
        Асинхронно ищет релевантную информацию по запросу.
        
        Args:
            query: Текст запроса от пользователя.
            max_results: Максимальное количество документов.
            threshold: Порог схожести (0.0 - 1.0), где 1.0 - полное совпадение.
            
        Returns:
            Конкатенированная строка релевантного контекста.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._get_context_sync, query, max_results, threshold)

    def _get_context_sync(self, query: str, max_results: int, threshold: float) -> str:
        """Синхронная логика запроса к ChromaDB."""
        try:
            # Для поиска используем префикс 'query: '
            prefixed_query = f"query: {query}"
            
            results = self.collection.query(
                query_texts=[prefixed_query],
                n_results=max_results
            )
            
            if not results['documents'] or not results['documents'][0]:
                return ""
            
            # Фильтрация по порогу схожести
            valid_docs = []
            for doc, dist in zip(results['documents'][0], results['distances'][0]):
                # Для L2: меньшая дистанция = большее сходство. 
                # Косвенная оценка: 1 - (dist/2) (примерно для нормализованных векторов)
                similarity = 1.0 / (1.0 + dist)
                if similarity >= threshold:
                    valid_docs.append(doc)
            
            if not valid_docs:
                logger.debug(f"🔍 Нет документов выше порога {threshold} (лучший match similarity: {1.0/(1.0+results['distances'][0][0]):.4f})")
                return ""
                
            return "\n---\n".join(valid_docs)
        except Exception as e:
            logger.error(f"⚠️ Ошибка RAG запроса: {e}")
            return ""

    @property
    def chroma_client(self):
        """Доступ к JSON клиенту Chroma для эскалации."""
        return self.client

class MockRAGSystem:
    """Заглушка для RAG, если база данных недоступна."""
    async def get_context_for_query(self, query: str, **kwargs) -> str:
        return ""
