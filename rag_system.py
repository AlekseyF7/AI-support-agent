"""RAG система для ответов на типовые вопросы"""
import json
import os
from typing import List, Optional
import warnings
import logging

# Полностью отключаем телеметрию chromadb ДО импорта
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_DISABLED"] = "1"
os.environ["ALLOW_RESET"] = "TRUE"  # Дополнительная настройка

# Подавляем предупреждения urllib3 и SSL
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Подавляем ошибки tqdm (проблема с библиотекой)
import sys
import atexit

# Подавляем ошибки tqdm до импорта
try:
    import tqdm
    # Сохраняем оригинальный __del__
    if hasattr(tqdm.tqdm, '__del__'):
        original_tqdm_del = tqdm.tqdm.__del__
        
        def safe_tqdm_del(self):
            """Безопасное удаление tqdm объекта"""
            try:
                # Проверяем наличие необходимых атрибутов
                if hasattr(self, 'last_print_t') and hasattr(self, 'start_t') and hasattr(self, 'delay'):
                    original_tqdm_del(self)
            except (AttributeError, Exception):
                # Игнорируем все ошибки при удалении
                pass
        
        # Переопределяем __del__
        tqdm.tqdm.__del__ = safe_tqdm_del
except (ImportError, AttributeError, Exception):
    # Если tqdm не установлен или есть проблемы, игнорируем
    pass

# Подавляем все логи телеметрии ДО импорта chromadb
telemetry_logger = logging.getLogger("chromadb.telemetry")
telemetry_logger.setLevel(logging.CRITICAL)
telemetry_logger.disabled = True

# Подавляем posthog логи
posthog_logger = logging.getLogger("chromadb.telemetry.product.posthog")
posthog_logger.setLevel(logging.CRITICAL)
posthog_logger.disabled = True

try:
    # Перехватываем все ошибки телеметрии при импорте
    import sys
    from io import StringIO
    
    # Временно перенаправляем stderr для подавления ошибок телеметрии
    old_stderr = sys.stderr
    sys.stderr = StringIO()
    
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from chromadb.utils import embedding_functions
        CHROMADB_AVAILABLE = True
    finally:
        # Восстанавливаем stderr
        sys.stderr = old_stderr
        
except ImportError as e:
    CHROMADB_AVAILABLE = False
    warnings.warn(f"ChromaDB не доступен: {e}. RAG система будет работать в упрощенном режиме.")
except Exception as e:
    # Если произошла любая другая ошибка при импорте (например, телеметрия)
    CHROMADB_AVAILABLE = False
    logger.warning(f"Ошибка при импорте ChromaDB: {e}. Используется упрощенный режим.")

from config import settings


class RAGSystem:
    """Система RAG для поиска релевантных ответов"""
    
    def __init__(self):
        self.chromadb_available = CHROMADB_AVAILABLE
        self.knowledge_base = {}  # Простое хранилище для упрощенного режима
        self.embedding_model_name = None  # Название используемой модели
        
        if self.chromadb_available:
            try:
                self._initialize_chromadb()
                logger.info("ChromaDB успешно инициализирован")
            except Exception as e:
                logger.warning(f"Ошибка инициализации ChromaDB: {e}. Используется упрощенный режим.")
                self.chromadb_available = False
                self._initialize_simple_knowledge_base()
        else:
            self._initialize_simple_knowledge_base()
    
    def _initialize_chromadb(self):
        """Инициализация ChromaDB с embedding функцией"""
        # Создаем клиент ChromaDB
        try:
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_DB_PATH,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
        except TypeError:
            # Новые версии ChromaDB могут не поддерживать settings параметр
            self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        
        # Отключаем телеметрию через логгеры
        for logger_name in ["chromadb.telemetry", "chromadb.telemetry.product", "chromadb.telemetry.product.posthog"]:
            tel_logger = logging.getLogger(logger_name)
            tel_logger.setLevel(logging.CRITICAL)
            tel_logger.disabled = True
        
        # Загружаем embedding функцию
        embedding_func = self._load_embedding_function()
        
        # Получаем или создаем коллекцию
        try:
            if embedding_func:
                self.collection = self.client.get_collection(
                    name="support_knowledge_base",
                    embedding_function=embedding_func
                )
            else:
                self.collection = self.client.get_collection(name="support_knowledge_base")
            logger.info(f"Загружена существующая коллекция (документов: {self.collection.count()})")
        except Exception:
            # Коллекция не существует, создаем новую
            if embedding_func:
                self.collection = self.client.create_collection(
                    name="support_knowledge_base",
                    embedding_function=embedding_func
                )
            else:
                self.collection = self.client.create_collection(name="support_knowledge_base")
            logger.info("Создана новая коллекция")
        
        # Инициализируем базу знаний
        self._initialize_knowledge_base()
    
    def _load_embedding_function(self):
        """Загрузка embedding функции с fallback"""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            logger.warning("sentence-transformers не установлен. Используется встроенная функция ChromaDB.")
            return None
        
        # Список моделей для попытки загрузки (от лучших для русского к универсальным)
        # Используем полные имена с HuggingFace Hub
        models_to_try = [
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
            "sentence-transformers/distiluse-base-multilingual-cased-v2",
            "sentence-transformers/all-MiniLM-L6-v2",
        ]
        
        # Добавляем модель из настроек в начало, если она указана
        config_model = settings.EMBEDDING_MODEL
        if config_model:
            # Добавляем префикс если его нет
            if not config_model.startswith("sentence-transformers/"):
                config_model = f"sentence-transformers/{config_model}"
            if config_model not in models_to_try:
                models_to_try.insert(0, config_model)
        
        for model_name in models_to_try:
            try:
                logger.info(f"Загружаю embedding модель: {model_name}")
                
                # Пробуем загрузить модель напрямую
                test_model = SentenceTransformer(model_name)
                
                # Проверяем что модель реально загрузилась и работает
                test_embedding = test_model.encode("тестовое предложение для проверки", show_progress_bar=False)
                
                if test_embedding is None or len(test_embedding) == 0:
                    raise ValueError("Модель вернула пустой embedding")
                
                logger.info(f"✓ Модель {model_name} успешно загружена, размерность: {len(test_embedding)}")
                
                # Используем эту модель напрямую (не через ChromaDB embedding function)
                # Создаем кастомную embedding функцию
                class CustomEmbeddingFunction:
                    def __init__(self, model):
                        self.model = model
                    
                    def __call__(self, input):
                        return self.model.encode(input, show_progress_bar=False).tolist()
                
                embedding_func = CustomEmbeddingFunction(test_model)
                self.embedding_model_name = model_name
                logger.info(f"✓ Успешно загружена embedding модель: {model_name}")
                return embedding_func
                
            except Exception as e:
                logger.warning(f"Не удалось загрузить модель {model_name}: {e}")
                continue
        
        logger.warning("Не удалось загрузить ни одну embedding модель. Используется встроенная функция ChromaDB.")
        return None
    
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
        try:
            count = self.collection.count()
        except Exception as e:
            logger.warning(f"Ошибка при подсчете документов: {e}")
            count = 0
            
        if count == 0:
            logger.info("База знаний пуста, добавляю начальные документы...")
            # Добавляем типовые вопросы и ответы для банковской тематики
            knowledge_base = [
                {
                    "id": "faq_1",
                    "text": "Как сбросить пароль от Сбербанк Онлайн? Для сброса пароля перейдите в приложение, нажмите 'Забыли пароль?' и следуйте инструкциям. Вы можете восстановить доступ по номеру карты или через СМС.",
                    "metadata": {"category": "account", "tags": "пароль, сброс, восстановление, сбербанк онлайн"}
                },
                {
                    "id": "faq_2",
                    "text": "Как оплатить услуги через Сбербанк? Оплата производится через мобильное приложение Сбербанк Онлайн или через банкоматы. Доступны карты Visa, MasterCard, МИР.",
                    "metadata": {"category": "billing", "tags": "оплата, платеж, карта, услуги"}
                },
                {
                    "id": "faq_3",
                    "text": "Как связаться с техподдержкой Сбербанка? Позвоните по номеру 900 (бесплатно с мобильного) или 8-800-555-55-50. Также можно написать в чат поддержки в приложении.",
                    "metadata": {"category": "other", "tags": "контакты, поддержка, телефон, 900"}
                },
                {
                    "id": "faq_4",
                    "text": "Что делать если не работает Сбербанк Онлайн? Проверьте интернет-соединение, обновите приложение до последней версии. Если проблема сохраняется, очистите кеш приложения или обратитесь в поддержку.",
                    "metadata": {"category": "technical", "tags": "ошибка, не работает, приложение, сбой"}
                },
                {
                    "id": "faq_5",
                    "text": "Как изменить данные профиля в Сбербанке? Для изменения личных данных обратитесь в отделение банка с паспортом. Некоторые данные можно изменить через приложение.",
                    "metadata": {"category": "account", "tags": "профиль, настройки, данные, изменение"}
                },
                {
                    "id": "faq_6",
                    "text": "Как заблокировать карту Сбербанка? Заблокировать карту можно через приложение Сбербанк Онлайн, по телефону 900, или через банкомат. Блокировка происходит мгновенно.",
                    "metadata": {"category": "account", "tags": "блокировка, карта, потеря, кража"}
                },
                {
                    "id": "faq_7",
                    "text": "Как перевести деньги на карту другого банка? В приложении Сбербанк Онлайн выберите 'Переводы', затем 'На карту в другой банк'. Введите номер карты получателя и сумму.",
                    "metadata": {"category": "billing", "tags": "перевод, другой банк, карта, деньги"}
                }
            ]
            
            texts = [item["text"] for item in knowledge_base]
            ids = [item["id"] for item in knowledge_base]
            metadatas = [item["metadata"] for item in knowledge_base]
            
            try:
                self.collection.add(
                    documents=texts,
                    ids=ids,
                    metadatas=metadatas
                )
                logger.info(f"Добавлено {len(texts)} документов в базу знаний")
            except Exception as add_error:
                logger.warning(f"Ошибка при добавлении документов: {add_error}")
        else:
            logger.info(f"База знаний содержит {count} документов")
    
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
            logger.debug(f"Добавлен документ в базу знаний: {doc_id}")
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

