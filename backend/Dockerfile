# syntax=docker/dockerfile:1
# === Task Board backend: FastAPI + aiogram (один контейнер, Q-A1) ===
# Python 3.12 (план этапа 1). Multi-stage: builder (компиляция зависимостей)
# → runtime (чистый slim без build-essential).

# --- builder: установка зависимостей в отдельный prefix ---
FROM python:3.12-slim AS builder

# Инструменты сборки — только на случай пакетов без prebuilt wheel
# (sqlite-vec обычно ставится готовым wheel'ом).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- runtime: чистый образ ---
FROM python:3.12-slim

WORKDIR /app

# Зависимости из builder (без компилятора и apt-кэша).
COPY --from=builder /install /usr/local

# Код приложения.
COPY app/ ./app/

# Vault монтируется как volume (см. docker-compose.yml), поэтому его НЕ копируем.
# Создаём точку монтирования, чтобы при старте каталог существовал.
RUN mkdir -p /app/vault \
    && useradd --system --create-home appuser \
    && chown -R appuser:appuser /app

# Не root (актуально и для прав на vault-маунт; docker-compose может
# переопределить на user: UID:GID хоста).
USER appuser

# Порт uvicorn.
EXPOSE 8000

# Запуск через uvicorn. Для dev добавить --reload можно через override compose.
# За Caddy: доверяем X-Forwarded-Proto/For, иначе редиректы уходят на http://,
# а в логах IP прокси вместо клиента. "*" безопасно: порт 8000 только expose'нут
# во внутреннюю сеть compose, снаружи до uvicorn не достучаться.
# Exec-форма без shell — значение пишется без кавычек, иначе они уйдут в uvicorn.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips=*"]
