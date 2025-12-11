"""
Qdrant векторное хранилище для замены ChromaDB
"""
import os
from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain_qdrant import Qdrant
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from dotenv import load_dotenv

load_dotenv()


class QdrantVectorStore:
    """Qdrant векторное хранилище для RAG системы"""

    def __init__(
        self,
        collection_name: str = "knowledge_base",
        qdrant_url: Optional[str] = None,
        qdrant_api_key: Optional[str] = None
    ):
        self.collection_name = collection_name
        qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_api_key = qdrant_api_key or os.getenv("QDRANT_API_KEY")

        # Инициализация клиента Qdrant
        if qdrant_api_key:
            self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        else:
            self.client = QdrantClient(url=qdrant_url)

        # Определение провайдера embeddings
        llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()

        if llm_provider == "ollama":
            ollama_model = os.getenv("OLLAMA_MODEL", "mistral")
            ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            self.embeddings = OllamaEmbeddings(
                model=ollama_model,
                base_url=ollama_base_url
            )
            print(f"[INFO] Используется Ollama embeddings: {ollama_model}")
        else:
            openai_kwargs = {}
            if os.getenv("OPENAI_PROXY"):
                import httpx
                proxy_url = os.getenv("OPENAI_PROXY")
                openai_kwargs["http_client"] = httpx.Client(proxies=proxy_url, timeout=60.0)
            if os.getenv("OPENAI_BASE_URL"):
                openai_kwargs["base_url"] = os.getenv("OPENAI_BASE_URL")

            self.embeddings = OpenAIEmbeddings(**openai_kwargs)
            print(f"[INFO] Используется OpenAI embeddings")

        # Инициализация векторного хранилища
        self.vectorstore = None
        self._init_collection()

    def _init_collection(self):
        """Инициализация коллекции в Qdrant"""
        try:
            # Проверяем существование коллекции
            collections = self.client.get_collections().collections
            collection_exists = any(c.name == self.collection_name for c in collections)

            if not collection_exists:
                # Создаем коллекцию
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=1536 if "openai" in str(self.embeddings).lower() else 4096,
                        distance=Distance.COSINE
                    )
                )
                print(f"[INFO] Создана коллекция Qdrant: {self.collection_name}")

            # Инициализируем LangChain Qdrant
            self.vectorstore = Qdrant(
                client=self.client,
                collection_name=self.collection_name,
                embeddings=self.embeddings
            )
        except Exception as e:
            print(f"[ERROR] Ошибка инициализации Qdrant: {e}")
            raise

    def load_knowledge_base(self, knowledge_base_path: str = "knowledge_base"):
        """Загрузка и индексация базы знаний"""
        print(f"Загрузка базы знаний из {knowledge_base_path}...")

        # Загрузка документов
        loader = DirectoryLoader(
            knowledge_base_path,
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={'encoding': 'utf-8'}
        )
        documents = loader.load()

        if not documents:
            print("Предупреждение: не найдено документов в базе знаний")
            return

        print(f"Загружено {len(documents)} документов")

        # Разбиение на чанки
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_documents(documents)
        print(f"Создано {len(chunks)} чанков")

        # Добавление в Qdrant
        if chunks:
            self.vectorstore.add_documents(chunks)
            print(f"[INFO] База знаний загружена в Qdrant коллекцию: {self.collection_name}")

    def search(self, query: str, k: int = 4) -> List:
        """Поиск похожих документов"""
        if not self.vectorstore:
            raise ValueError("Vector store не инициализирован")

        return self.vectorstore.similarity_search(query, k=k)

    def search_with_score(self, query: str, k: int = 4) -> List:
        """Поиск с оценкой схожести"""
        if not self.vectorstore:
            raise ValueError("Vector store не инициализирован")

        return self.vectorstore.similarity_search_with_score(query, k=k)

    def delete_collection(self):
        """Удаление коллекции"""
        try:
            self.client.delete_collection(self.collection_name)
            print(f"[INFO] Коллекция {self.collection_name} удалена")
        except Exception as e:
            print(f"[ERROR] Ошибка удаления коллекции: {e}")

    def get_collection_info(self) -> dict:
        """Получение информации о коллекции"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                "name": collection_info.name,
                "vectors_count": collection_info.points_count,
                "config": {
                    "size": collection_info.config.params.vectors.size,
                    "distance": collection_info.config.params.vectors.distance.name
                }
            }
        except Exception as e:
            print(f"[ERROR] Ошибка получения информации о коллекции: {e}")
            return {}
