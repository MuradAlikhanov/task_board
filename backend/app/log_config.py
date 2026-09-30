"""Настройка логирования (structlog + stdlib).

Вызывается один раз при старте процесса: `create_app()` и точка входа CLI.
Модульные `structlog.get_logger()` — ленивые прокси, поэтому их можно создавать
на уровне модуля до вызова `setup_logging()`.

- Уровень — из `LOG_LEVEL` (ARCHITECTURE §8): ниже уровня записи отбрасываются.
- development: читаемый вывод в консоль; production: JSON-строка на запись.
- Библиотеки на stdlib logging (aiogram, watchdog) — тот же уровень, свой формат.
"""
from __future__ import annotations

import logging
import sys

import structlog

from app.config import Settings


def setup_logging(settings: Settings) -> None:
    """Настраивает structlog и корневой stdlib-логгер по настройкам."""
    level = getattr(logging, settings.log_level)

    processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]
    if settings.is_production:
        processors += [
            structlog.processors.format_exc_info,
            # Кириллица в логах читаемой, а не \uXXXX.
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ]
    else:
        # Цвета только в терминале: в `docker compose logs` ANSI-коды — мусор.
        processors.append(structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty()))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Логгеры uvicorn настраивает сам (propagate=False) — дублей не будет.
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    # watchdog на DEBUG пишет каждое сырое inotify-событие — события vault
    # и так логирует watcher.file_event.
    logging.getLogger("watchdog").setLevel(max(level, logging.INFO))
