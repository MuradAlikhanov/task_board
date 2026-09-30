"""FastAPI приложение Task Board.

Точка входа: uvicorn app.main:app (см. backend/Dockerfile CMD).

Включает:
- lifespan (старт/стоп бота, watcher, шины событий) — ARCHITECTURE §10 Q-A1.
- CORS middleware.
- Health-роуты /healthz, /ready — ARCHITECTURE §7.
- Базовый роут / и /api/v1/ (приветствие/статус).

Бизнес-роуты (задачи, контакты, wiki) — этап 3.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.api.routes import health
from app.bot import bot as bot_module
from app.db.connection import init_db
from app.events.bus import get_event_bus
from app.indexer.watcher import start_watcher, stop_watcher
from app.log_config import setup_logging

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Жизненный цикл приложения.

    Здесь поднимаются фоновые подсистемы (Q-A1): бот, watcher, шина событий.
    На этапе 1 они либо заглушки, либо работают в «пустом» режиме.
    """
    settings: Settings = get_settings()

    # Инициализация шины событий (Q-A1).
    _ = get_event_bus()
    log.info("lifespan.start", env=settings.app_env, bot_mode=settings.bot_mode)

    # Vault не создаём: он примонтирован (volume) или синхронизирован Syncthing.
    # Если его нет (опечатка в VAULT_PATH, не смонтирован) — процесс не роняем,
    # а /ready отвечает 503, пока конфигурацию не исправят и не перезапустят.
    observer = None
    if settings.vault_path.is_dir():
        # Индекс создаём один раз при старте: /ready открывает его только на чтение.
        init_db()
        # Vault watcher (этап 3 — реальная индексация; сейчас логирует события).
        observer = start_watcher(settings)
    else:
        log.error("lifespan.vault_missing", path=str(settings.vault_path))

    # Бот (Q-A1, Q-A4). На этапе 1 токен обычно не задан — бот пропускается.
    try:
        bot_module.init_bot(settings)
        await bot_module.start_bot(settings)
    except RuntimeError as exc:
        # Нормально для dev без токена — просто логируем.
        log.warning("lifespan.bot_skipped", reason=str(exc))

    try:
        yield
    finally:
        # Корректный shutdown в обратном порядке.
        await bot_module.stop_bot()
        if observer is not None:
            stop_watcher(observer)
        log.info("lifespan.stop")


def create_app() -> FastAPI:
    """Фабрика приложения."""
    settings = get_settings()
    setup_logging(settings)

    app = FastAPI(
        title="Task Board API",
        version="0.1.0",
        description="Управление сопровождением проектов: заявки, wiki, Telegram, ИИ.",
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/api/v1/openapi.json",
        lifespan=lifespan,
    )

    # CORS (ARCHITECTURE §6.3 — origins из .env).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health-роуты на корне (используются Docker HEALTHCHECK и Caddy).
    app.include_router(health.router)

    @app.get("/", tags=["root"], summary="Корень сервиса")
    async def root() -> dict[str, str]:
        """Приветствие/статус — для быстрой проверки прокси."""
        return {"service": "Task Board", "status": "running", "env": settings.app_env}

    @app.get("/api/v1", tags=["root"], summary="API корень")
    async def api_root() -> dict[str, str]:
        return {"name": "Task Board API", "version": "0.1.0"}

    # TODO(этап 2): подключить роуты авторизации (app.api.routes.auth).
    # TODO(этап 3): подключить роуты задач/контактов/wiki (app.api.routes.*).
    return app


# uvicorn app.main:app
app = create_app()
