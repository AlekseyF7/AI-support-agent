"""
Конфигурация LLM провайдеров
Поддерживает различные провайдеры: OpenAI, Ollama, Groq, Hugging Face
"""
import os
from typing import Optional

def get_llm(provider: Optional[str] = None):
    """
    Создает LLM клиент в зависимости от провайдера
    
    Args:
        provider: 'openai', 'ollama', 'groq', 'huggingface' или None (автоопределение)
    
    Returns:
        LLM клиент
    """
    # Автоопределение провайдера
    if provider is None:
        if os.getenv("GROQ_API_KEY"):
            provider = "groq"
        elif os.getenv("HUGGINGFACE_API_KEY"):
            provider = "huggingface"
        elif os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_MODEL"):
            provider = "ollama"
        else:
            provider = "openai"  # По умолчанию
    
    # OpenAI
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        
        openai_kwargs = {}
        if os.getenv("OPENAI_PROXY"):
            import httpx
            proxy_url = os.getenv("OPENAI_PROXY")
            openai_kwargs["http_client"] = httpx.Client(proxies=proxy_url, timeout=60.0)
        if os.getenv("OPENAI_BASE_URL"):
            openai_kwargs["base_url"] = os.getenv("OPENAI_BASE_URL")
        
        return ChatOpenAI(
            temperature=0,
            model_name=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            **openai_kwargs
        )
    
    # Groq
    elif provider == "groq":
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                model_name=os.getenv("GROQ_MODEL", "llama2-70b-4096"),
                groq_api_key=os.getenv("GROQ_API_KEY")
            )
        except ImportError:
            raise ImportError("langchain-groq не установлен. Установите: pip install langchain-groq")
    
    # Ollama
    elif provider == "ollama":
        from langchain_community.llms import Ollama
        model = os.getenv("OLLAMA_MODEL", "mistral")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return Ollama(model=model, base_url=base_url)
    
    # Hugging Face
    elif provider == "huggingface":
        try:
            from langchain_community.llms import HuggingFaceHub
            return HuggingFaceHub(
                repo_id=os.getenv("HUGGINGFACE_MODEL", "meta-llama/Llama-2-7b-chat-hf"),
                huggingfacehub_api_token=os.getenv("HUGGINGFACE_API_KEY")
            )
        except ImportError:
            raise ImportError("huggingface_hub не установлен. Установите: pip install huggingface_hub")
    
    else:
        raise ValueError(f"Неизвестный провайдер: {provider}")


def get_embeddings(provider: Optional[str] = None):
    """
    Создает embeddings клиент
    
    Args:
        provider: 'openai', 'ollama' или None (автоопределение)
    
    Returns:
        Embeddings клиент
    """
    if provider is None:
        if os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_MODEL"):
            provider = "ollama"
        else:
            provider = "openai"
    
    # OpenAI Embeddings
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        
        openai_kwargs = {}
        if os.getenv("OPENAI_PROXY"):
            import httpx
            proxy_url = os.getenv("OPENAI_PROXY")
            openai_kwargs["http_client"] = httpx.Client(proxies=proxy_url, timeout=60.0)
        if os.getenv("OPENAI_BASE_URL"):
            openai_kwargs["base_url"] = os.getenv("OPENAI_BASE_URL")
        
        return OpenAIEmbeddings(**openai_kwargs)
    
    # Ollama Embeddings
    elif provider == "ollama":
        from langchain_community.embeddings import OllamaEmbeddings
        model = os.getenv("OLLAMA_MODEL", "mistral")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return OllamaEmbeddings(model=model, base_url=base_url)
    
    else:
        raise ValueError(f"Неизвестный провайдер для embeddings: {provider}")

