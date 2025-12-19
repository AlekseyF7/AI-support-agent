# --- Stage 1: Builder ---
FROM python:3.11-slim as builder

WORKDIR /app

# 1. Установка системных зависимостей (Кэшируется отдельно)
# Добавляем зависимости для Playwright/Chromium
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 2. Установка библиотек
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 3. Установка браузеров Playwright
RUN python -m playwright install chromium --with-deps

# 4. Настройка модели
ARG EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-small
ENV EMBEDDING_MODEL_NAME=${EMBEDDING_MODEL_NAME}

COPY download_model.py .
RUN python download_model.py "${EMBEDDING_MODEL_NAME}"

# --- Stage 2: Final ---
FROM python:3.11-slim

# Системные зависимости в финальном образе (добавляем libxfixes3 и libnspr4)
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копирование из builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /root/.cache /root/.cache

# Окружение
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY . .
RUN mkdir -p chroma_db

CMD ["python", "bot.py"]
