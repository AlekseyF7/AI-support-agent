""" 
Клиент для интеграции со Sber Salute Speech (распознавание речи).
Работает через SmartSpeech REST API с поддержкой асинхронного HTTPX.
"""
import base64
import time
import uuid
import logging
from typing import Optional, Tuple
import httpx

logger = logging.getLogger(__name__)

# Эндпоинты авторизации и распознавания
TOKEN_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
STT_URL = "https://smartspeech.sber.ru/rest/v1/speech:recognize"

class SaluteSpeechClient:
    """
    Асинхронный клиент для Salute Speech STT.
    Автоматически управляет жизненным циклом токена доступа.
    """

    def __init__(self, client_id: str, client_secret: str):
        """
        Инициализация клиента.
        
        Args:
            client_id: ID клиента сервиса.
            client_secret: Секрет или готовый ключ авторизации.
        """
        self.client_id = (client_id or "").strip()
        self.client_secret = (client_secret or "").strip()
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        
        # Определение типа секрета (явный ключ или ID:Secret)
        self._secret_is_auth_key = '==' in self.client_secret or (
            len(self.client_secret) > 50 and ':' not in self.client_secret
        )

        # HTTP клиент с поддержкой таймаутов
        self.client = httpx.AsyncClient(
            verify=False,  # Необходим для работы с сертификатами Минцифры/Сбера
            timeout=httpx.Timeout(30.0, read=60.0),
            limits=httpx.Limits(max_connections=10)
        )

    def _get_basic_auth_header(self) -> str:
        """Формирует заголовок Basic Auth."""
        if self._secret_is_auth_key:
            return self.client_secret
        auth_bytes = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        return base64.b64encode(auth_bytes).decode("utf-8")

    async def _update_token(self):
        """Обновляет токен доступа, если текущий истек или скоро истечет."""
        if not self.client_id or not self.client_secret:
            return

        # Обновляем, если до истечения осталось меньше 30 секунд
        if self._access_token and time.time() < self._token_expires_at - 30:
            return

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"Basic {self._get_basic_auth_header()}",
        }
        
        try:
            logger.debug("🔄 Обновление токена Salute Speech...")
            response = await self.client.post(
                TOKEN_URL,
                headers=headers,
                data={"scope": "SALUTE_SPEECH_PERS"}
            )
            response.raise_for_status()
            
            data = response.json()
            self._access_token = data["access_token"]
            # Конвертируем миллисекунды в секунды (Unix timestamp)
            self._token_expires_at = (data.get("expires_at", time.time() * 1000 + 1800000) / 1000)
            logger.info("✅ Токен Salute Speech успешно обновлен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления токена Salute Speech: {e}")
            raise

    async def recognize(self, audio_data: bytes, content_type: str = "audio/ogg;codecs=opus") -> Tuple[str, bool]:
        """
        Преобразует аудио в текст.
        
        Args:
            audio_data: Байты аудиофайла (OGG/OPUS или WAV).
            content_type: MIME-тип аудио.
            
        Returns:
            Tuple[str, bool]: Распознанный текст и флаг успеха.
        """
        if not self.client_id or not self.client_secret:
            return "", False

        try:
            await self._update_token()
            
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": content_type,
            }

            response = await self.client.post(
                STT_URL,
                headers=headers,
                content=audio_data
            )
            
            if response.status_code == 200:
                data = response.json()
                # API может возвращать результат в полях 'result' или 'results'
                text = ""
                if "result" in data and data["result"]:
                    text = data["result"][0]
                elif "results" in data and data["results"]:
                    text = data["results"][0].get("normalized_text", "")
                
                if text:
                    logger.debug("🎤 Распознано: %s", text)
                    return text.strip(), True
                return "", False
            else:
                logger.error(f"⚠️ STT API вернул ошибку {response.status_code}: {response.text}")
                return "", False

        except Exception as e:
            logger.error(f"❌ Исключение при распознавании речи: {e}")
            return "", False

    async def close(self):
        """Закрывает HTTP соединения."""
        await self.client.aclose()
        logger.info("🛡️ Salute Speech клиент закрыт")
