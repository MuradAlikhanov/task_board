# syntax=docker/dockerfile:1
# === Task Board backend: FastAPI + aiogram (один контейнер, Q-A1) ===
# Python 3.14 (как в requirements.txt). Multi-stage: builder (компиляция зависимостей)
# → runtime (чистый slim без build-essential).

# --- builder: установка зависимостей в отдельный prefix ---
FROM python:3.14-slim AS builder

# Инструменты сборки — только на случай пакетов без prebuilt wheel
# (sqlite-vec обычно ставится готовым wheel'ом).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- runtime: чистый образ ---
FROM python:3.14-slim

WORKDIR /app

# Зависимости из builder (без компилятора и apt-кэша).
COPY --from=builder /install /usr/local

# Код приложения.
COPY app/ ./app/

# Vault и каталог индекса монтируются как volumes (см. docker-compose.yml),
# поэтому их НЕ копируем. Создаём точки монтирования, чтобы каталоги существовали.
RUN mkdir -p /app/vault /app/db \
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
