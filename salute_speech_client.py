"""Клиент для распознавания речи через Sber Salute Speech (SmartSpeech REST API)."""

import base64
import time
import uuid
import json
from typing import Optional
import ssl
import http.client
from urllib.parse import urlparse

TOKEN_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
STT_URL = "https://smartspeech.sber.ru/rest/v1/speech:recognize"

# Создаем SSL контекст с полностью отключенной проверкой
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE


class SaluteSpeechClient:
    """Простой клиент для распознавания речи через Salute Speech."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = (client_id or "").strip()
        self.client_secret = (client_secret or "").strip()
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        
        # Определяем, является ли secret уже base64-закодированным Authorization Key
        # Сбер выдает client_secret уже в формате base64 (содержит == в конце)
        self._secret_is_auth_key = '==' in self.client_secret or (
            len(self.client_secret) > 50 and ':' not in self.client_secret
        )

    def _has_credentials(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _get_basic_auth_header(self) -> str:
        # Если secret уже является готовым Authorization Key (base64), используем его напрямую
        if self._secret_is_auth_key:
            return self.client_secret
        
        # Иначе формируем base64(client_id:client_secret)
        auth_bytes = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        return base64.b64encode(auth_bytes).decode("utf-8")

    def _make_request(self, method: str, url: str, headers: dict = None, body: bytes = None, fields: dict = None) -> tuple[int, bytes]:
        """Делает HTTP запрос с отключенной проверкой SSL."""
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        path = parsed.path or '/'
        if parsed.query:
            path += '?' + parsed.query

        # Создаем HTTPS соединение с отключенной проверкой SSL
        conn = http.client.HTTPSConnection(host, port, context=SSL_CONTEXT)
        
        try:
            # Если есть fields, формируем form data
            if fields:
                import urllib.parse
                body = urllib.parse.urlencode(fields).encode('utf-8')
                if headers is None:
                    headers = {}
                if 'Content-Type' not in headers:
                    headers['Content-Type'] = 'application/x-www-form-urlencoded'

            conn.request(method, path, body, headers or {})
            response = conn.getresponse()
            response_data = response.read()
            return response.status, response_data
        finally:
            conn.close()

    def _update_token(self):
        """Запрашивает новый access_token, если он отсутствует или истёк."""
        if not self._has_credentials():
            raise RuntimeError(
                "Не заданы SALUTE_SPEECH_CLIENT_ID / SALUTE_SPEECH_CLIENT_SECRET. "
                "Голосовое распознавание недоступно."
            )

        # Если текущий токен ещё жив, ничего не делаем
        if self._access_token and time.time() < self._token_expires_at - 10:
            return

        # Формируем заголовки согласно документации API
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),  # Уникальный идентификатор запроса
            "Authorization": f"Basic {self._get_basic_auth_header()}",
        }
        
        # Используем scope вместо grant_type согласно документации
        fields = {
            "scope": "SALUTE_SPEECH_PERS"
        }

        # Делаем запрос
        try:
            status, response_data = self._make_request('POST', TOKEN_URL, headers=headers, fields=fields)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка при запросе токена: {e}", exc_info=True)
            raise RuntimeError(f"Не удалось получить токен: {e}")

        if status != 200:
            error_text = response_data.decode('utf-8', errors='ignore')
            raise RuntimeError(
                f"Ошибка получения токена: HTTP {status} - {error_text}"
            )

        try:
            payload = json.loads(response_data.decode('utf-8'))
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Не удалось распарсить ответ API: {e}")

        self._access_token = payload.get("access_token")
        if not self._access_token:
            raise RuntimeError(f"Токен не найден в ответе API: {payload}")
        
        expires_in = payload.get("expires_in", 600)
        self._token_expires_at = time.time() + int(expires_in)

    def recognize_file(self, file_path: str, content_type: str = "audio/ogg") -> str:
        """Распознаёт речь в аудиофайле и возвращает текст."""
        import logging
        import os
        logger = logging.getLogger(__name__)
        
        self._update_token()
        
        # Определяем content-type на основе расширения файла, если не указан явно
        file_ext = os.path.splitext(file_path)[1].lower()
        content_type_map = {
            ".ogg": "audio/ogg;codecs=opus",
            ".opus": "audio/ogg;codecs=opus", 
            ".wav": "audio/x-pcm;bit=16;rate=16000",
            ".mp3": "audio/mpeg",
            ".flac": "audio/flac",
        }
        
        # Используем правильный content-type для OGG файлов (Telegram отправляет OGG/Opus)
        if content_type == "audio/ogg" and file_ext in [".ogg", ".oga"]:
            content_type = "audio/ogg;codecs=opus"
        elif file_ext in content_type_map and content_type == "audio/ogg":
            content_type = content_type_map[file_ext]
        
        logger.info(f"Распознавание файла: {file_path}, content-type: {content_type}")

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": content_type,
        }

        with open(file_path, "rb") as f:
            audio_data = f.read()
        
        logger.info(f"Размер аудио данных: {len(audio_data)} байт")

        # Делаем запрос
        try:
            status, response_data = self._make_request('POST', STT_URL, headers=headers, body=audio_data)
        except Exception as e:
            logger.error(f"Ошибка при запросе к Salute Speech API: {e}", exc_info=True)
            raise RuntimeError(f"Не удалось распознать речь: {e}")

        if status != 200:
            error_text = response_data.decode('utf-8', errors='ignore')
            logger.error(f"Salute Speech API error: HTTP {status} - {error_text}")
            
            # Более информативные сообщения об ошибках
            if status == 401:
                raise RuntimeError("Ошибка авторизации Salute Speech. Проверьте CLIENT_ID и CLIENT_SECRET.")
            elif status == 400:
                raise RuntimeError(f"Неверный формат аудио или запроса: {error_text}")
            elif status == 413:
                raise RuntimeError("Файл слишком большой для обработки.")
            elif status == 429:
                raise RuntimeError("Превышен лимит запросов к API. Попробуйте позже.")
            else:
                raise RuntimeError(f"Ошибка распознавания речи: HTTP {status} - {error_text}")

        try:
            result_json = json.loads(response_data.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Не удалось распарсить ответ Salute Speech API: {e}")
            logger.error(f"Raw response: {response_data[:500]}")
            raise RuntimeError(f"Не удалось распарсить ответ API: {e}")

        logger.debug(f"Salute Speech API response: {result_json}")
        
        # Пробуем разные варианты формата ответа SmartSpeech API
        text = ""
        if isinstance(result_json, dict):
            # Вариант 1: {"result": ["текст1", "текст2"]} - массив результатов
            result_field = result_json.get("result")
            if isinstance(result_field, list) and result_field:
                text = " ".join(str(r) for r in result_field if r)
            elif isinstance(result_field, str):
                text = result_field
            
            # Вариант 2: {"results": [{"alternatives": [{"text": "текст", "confidence": 0.9}]}]}
            if not text and "results" in result_json:
                results = result_json.get("results", [])
                texts = []
                for result in results:
                    if isinstance(result, dict):
                        # Получаем alternatives и выбираем лучший по confidence
                        alternatives = result.get("alternatives", [])
                        if alternatives and isinstance(alternatives, list):
                            # Сортируем по confidence если есть
                            sorted_alts = sorted(
                                alternatives, 
                                key=lambda x: x.get("confidence", 0) if isinstance(x, dict) else 0,
                                reverse=True
                            )
                            best_alt = sorted_alts[0] if sorted_alts else {}
                            if isinstance(best_alt, dict):
                                alt_text = best_alt.get("text", "") or best_alt.get("transcript", "")
                                if alt_text:
                                    texts.append(alt_text)
                            elif isinstance(best_alt, str):
                                texts.append(best_alt)
                text = " ".join(texts)
            
            # Вариант 3: {"text": "текст"} - простой формат
            if not text:
                text = result_json.get("text", "")
            
            # Вариант 4: {"transcript": "текст"} - альтернативное поле
            if not text:
                text = result_json.get("transcript", "")
                
            # Вариант 5: {"status": "ok", "result": "текст"}
            if not text and result_json.get("status") == "ok":
                text = str(result_json.get("result", ""))
                
        elif isinstance(result_json, str):
            text = result_json
        elif isinstance(result_json, list):
            # Если вернулся просто массив строк
            text = " ".join(str(item) for item in result_json if item)
        
        if not text:
            logger.warning(f"Пустой результат распознавания. Полный ответ API: {result_json}")
            return ""
        
        logger.info(f"Успешно распознан текст ({len(text)} символов): {text[:100]}...")
        return text.strip()
