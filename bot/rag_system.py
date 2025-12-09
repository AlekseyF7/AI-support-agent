"""
RAG система для поиска ответов в базе знаний
"""
import os
from typing import List, Optional
try:
    from langchain_chroma import Chroma
except ImportError:
    # Fallback для старых версий
    from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


class RAGSystem:
    """Система RAG для работы с базой знаний"""
    
    def __init__(self, knowledge_base_path: str = "knowledge_base", db_path: str = "./chroma_db"):
        self.knowledge_base_path = knowledge_base_path
        self.db_path = db_path
        
        # Определение провайдера LLM
        llm_provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        
        if llm_provider == "ollama":
            # Использование Ollama для локальных моделей
            from langchain_community.llms import Ollama
            from langchain_community.embeddings import OllamaEmbeddings
            
            ollama_model = os.getenv("OLLAMA_MODEL", "mistral")
            ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            
            # Оптимизация для скорости: уменьшаем temperature и добавляем параметры
            self.llm = Ollama(
                model=ollama_model, 
                base_url=ollama_base_url,
                temperature=0.1,  # Низкая температура для более быстрых и детерминированных ответов
                num_predict=512,  # Ограничиваем длину ответа для ускорения
            )
            self.embeddings = OllamaEmbeddings(model=ollama_model, base_url=ollama_base_url)
            print(f"[INFO] Используется Ollama с моделью: {ollama_model} (оптимизировано для скорости)")
        else:
            # Использование OpenAI (по умолчанию или если указано)
            openai_kwargs = {}
            if os.getenv("OPENAI_PROXY"):
                openai_kwargs["http_client"] = self._create_proxy_client()
            if os.getenv("OPENAI_BASE_URL"):
                openai_kwargs["base_url"] = os.getenv("OPENAI_BASE_URL")
            
            self.embeddings = OpenAIEmbeddings(**openai_kwargs)
            self.llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", **openai_kwargs)
            print(f"[INFO] Используется OpenAI")
        self.vectorstore = None
        self.qa_chain = None
    
    def _create_proxy_client(self):
        """Создание HTTP клиента с прокси"""
        import httpx
        proxy_url = os.getenv("OPENAI_PROXY")
        return httpx.Client(proxies=proxy_url, timeout=60.0)
        
    def load_knowledge_base(self):
        """Загрузка и индексация базы знаний"""
        print("Загрузка базы знаний...")
        
        # Загрузка всех документов из базы знаний
        loader = DirectoryLoader(
            self.knowledge_base_path,
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={'encoding': 'utf-8'}
        )
        documents = loader.load()
        
        if not documents:
            print("Предупреждение: не найдено документов в базе знаний")
            return
        
        # Разбиение документов на чанки
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        texts = text_splitter.split_documents(documents)
        
        print(f"Загружено {len(documents)} документов, разбито на {len(texts)} чанков")
        
        # Отключение аналитики PostHog в ChromaDB
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        
        # Создание векторной БД
        if os.path.exists(self.db_path) and os.listdir(self.db_path):
            print("Загрузка существующей векторной БД...")
            self.vectorstore = Chroma(
                persist_directory=self.db_path,
                embedding_function=self.embeddings
            )
        else:
            print("Создание новой векторной БД...")
            self.vectorstore = Chroma.from_documents(
                documents=texts,
                embedding=self.embeddings,
                persist_directory=self.db_path
            )
        
        # Создание retriever с оптимизацией (меньше документов = быстрее)
        k_docs = int(os.getenv("RAG_K_DOCS", "2"))  # По умолчанию 2 вместо 3 для скорости
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": k_docs})
        
        # Создание промпта для ответа
        self.prompt_template = """Используй следующие фрагменты контекста из базы знаний для ответа на вопрос.
Если ты не знаешь ответа, просто скажи, что не знаешь, не пытайся придумать ответ.

Контекст: {context}

Вопрос: {question}

Ответ на русском языке:"""
        
        print("База знаний загружена и готова к использованию")
    
    def get_answer(self, question: str) -> dict:
        """
        Получить ответ на вопрос из базы знаний
        
        Args:
            question: Вопрос пользователя
            
        Returns:
            dict с полями:
                - answer: ответ
                - sources: источники информации
                - confidence: уверенность (можно добавить позже)
        """
        if not self.retriever:
            return {
                "answer": "База знаний не загружена. Пожалуйста, подождите.",
                "sources": [],
                "confidence": 0.0
            }
        
        # Проверка релевантности вопроса ПЕРЕД обработкой
        from .question_filter import QuestionFilter
        is_relevant, reason = QuestionFilter.is_relevant(question)
        if not is_relevant:
            print(f"[FILTER] Вопрос отклонен: {reason}")
            return {
                "answer": QuestionFilter.get_rejection_message(),
                "sources": [],
                "confidence": 0.0
            }
        
        try:
            # Поиск релевантных документов
            # В новых версиях LangChain используется invoke вместо get_relevant_documents
            docs = self.retriever.invoke(question)
            
            # Формирование контекста из найденных документов
            context = "\n\n".join([doc.page_content for doc in docs])
            
            # Если контекст пустой - это нормально, LLM может ответить на основе своих знаний
            # НЕ блокируем вопрос, так как он уже прошел проверку релевантности
            if not context or len(context.strip()) == 0:
                print(f"[RAG INFO] Контекст пустой, но вопрос релевантный - продолжаем обработку | Вопрос: {question[:50]}")
                # Используем минимальный контекст для LLM
                context = "Информация в базе знаний не найдена, но вопрос относится к технической поддержке."
            
            # Логируем длину контекста для отладки
            if len(context.strip()) < 50:
                print(f"[RAG INFO] Контекст короткий ({len(context.strip())} символов) | Вопрос: {question[:50]}")
            
            # Получение ответа от LLM с использованием ChatPromptTemplate
            # ВАЖНО: Строгие ограничения - отвечать ТОЛЬКО по функционалу поддержки
            chat_prompt = ChatPromptTemplate.from_messages([
                ("system", """Ты - помощник службы технической поддержки. 

КРИТИЧЕСКИ ВАЖНО - СТРОГО СОБЛЮДАЙ ЭТИ ПРАВИЛА:
1. Отвечай ТОЛЬКО на вопросы о:
   - Технических проблемах (не работает, ошибка, сбой)
   - Доступе к системам (пароль, логин, авторизация)
   - Программном обеспечении (установка, настройка, ошибки)
   - Оборудовании (принтер, компьютер, сеть)
   - IT-проблемах и настройках

2. НЕ отвечай на вопросы о:
   - Покупках, магазинах, товарах, фруктах, еде
   - Погоде, времени, развлечениях
   - Личных вопросах, общих знаниях
   - Вопросах, не связанных с IT/техникой

3. Если вопрос НЕ о технической поддержке:
   Ответь ТОЧНО: "Я могу помочь только с вопросами технической поддержки. Пожалуйста, задайте вопрос о работе систем, программного обеспечения или IT-проблемах."

4. Отвечай ТОЛЬКО на русском языке
5. Если в контексте есть информация - используй её для ответа
6. Если контекст пустой или не содержит нужной информации - дай общий ответ на основе твоих знаний о технической поддержке
7. Будь кратким и конкретным
8. Если не можешь дать ответ - скажи: "В базе знаний нет информации по этому вопросу. Обратитесь к специалисту."""),
                ("human", "Контекст: {context}\n\nВопрос: {question}\n\nВАЖНО: Ответь ТОЛЬКО если вопрос о технической поддержке. Если вопрос НЕ о техподдержке - скажи: 'Я могу помочь только с вопросами технической поддержки.'")
            ])
            
            # Для Ollama используем прямой вызов, для OpenAI - цепочку
            if hasattr(self.llm, 'invoke') and not isinstance(self.llm, type(self.llm).__bases__[0] if hasattr(type(self.llm), '__bases__') else None):
                # Проверяем, является ли это Chat моделью (OpenAI)
                try:
                    # OpenAI или другие Chat модели
                    from langchain_core.output_parsers import StrOutputParser
                    chain = chat_prompt | self.llm | StrOutputParser()
                    answer = chain.invoke({"context": context, "question": question})
                except:
                    # Если не работает как Chat модель, используем как обычный LLM
                    prompt_text = chat_prompt.format(context=context, question=question)
                    answer = self.llm.invoke(prompt_text)
            else:
                # Ollama (обычный LLM) - форматируем промпт вручную
                system_msg = """Ты - помощник службы технической поддержки. 

КРИТИЧЕСКИ ВАЖНО - СТРОГО СОБЛЮДАЙ:
1. Отвечай ТОЛЬКО на вопросы о технических проблемах, доступе, программах, оборудовании, IT
2. НЕ отвечай на вопросы о покупках, магазинах, фруктах, погоде, развлечениях, личных вопросах
3. Если вопрос НЕ о техподдержке - ответь ТОЧНО: "Я могу помочь только с вопросами технической поддержки. Пожалуйста, задайте вопрос о работе систем, программного обеспечения или IT-проблемах."
4. Отвечай ТОЛЬКО на русском языке
5. Если в контексте есть информация - используй её для ответа
6. Если контекст пустой - дай общий ответ на основе твоих знаний о технической поддержке
7. Будь кратким и конкретным"""
                user_msg = f"Контекст: {context}\n\nВопрос: {question}\n\nВАЖНО: Ответь ТОЛЬКО если вопрос о технической поддержке. Если вопрос НЕ о техподдержке - скажи: 'Я могу помочь только с вопросами технической поддержки.'"
                prompt_text = f"{system_msg}\n\n{user_msg}"
                answer = self.llm.invoke(prompt_text)
                
                # Дополнительная проверка ответа - если LLM все равно ответил не по теме
                if answer and not any(keyword in answer.lower() for keyword in [
                    "технической поддержки", "техподдержки", "it-проблем", "систем", 
                    "программ", "доступ", "пароль", "ошибка", "проблема", "настройка"
                ]):
                    # Проверяем, не является ли это ответом на нерелевантный вопрос
                    if any(irrelevant in question.lower() for irrelevant in ["магазин", "купить", "фрукты", "погода", "как дела"]):
                        answer = "Я могу помочь только с вопросами технической поддержки. Пожалуйста, задайте вопрос о работе систем, программного обеспечения или IT-проблемах."
            
            # Извлечение источников
            sources = []
            for doc in docs:
                if hasattr(doc, 'metadata'):
                    source = doc.metadata.get("source", "Unknown")
                    if source not in sources:
                        sources.append(source)
            
            if not answer:
                answer = "Извините, не удалось найти ответ в базе знаний. Обратитесь к специалисту."
            
            return {
                "answer": answer,
                "sources": sources,
                "confidence": 0.8  # Можно улучшить с помощью метрик
            }
        except Exception as e:
            error_msg = str(e)
            print(f"Ошибка при получении ответа: {e}")
            
            # Обработка ошибки недостаточной квоты
            if "429" in error_msg or "insufficient_quota" in error_msg.lower():
                return {
                    "answer": "Извините, закончился баланс на аккаунте OpenAI. Пожалуйста, пополните баланс на https://platform.openai.com/account/billing и попробуйте позже.",
                    "sources": [],
                    "confidence": 0.0
                }
            
            # Обработка других ошибок
            import traceback
            traceback.print_exc()
            return {
                "answer": "Извините, произошла ошибка при поиске ответа. Попробуйте переформулировать вопрос или обратитесь в поддержку.",
                "sources": [],
                "confidence": 0.0
            }
    
    def is_faq_question(self, question: str, answer: str) -> bool:
        """
        Определяет, является ли вопрос типовым FAQ
        
        Args:
            question: Вопрос пользователя
            answer: Ответ из базы знаний
            
        Returns:
            True если это типовой FAQ вопрос
        """
        # Простая эвристика: если ответ содержит структурированную информацию из FAQ
        faq_indicators = [
            "вопрос:",
            "ответ:",
            "для входа",
            "перейдите в",
            "обратитесь в",
            "используйте",
        ]
        
        answer_lower = answer.lower()
        return any(indicator in answer_lower for indicator in faq_indicators)

