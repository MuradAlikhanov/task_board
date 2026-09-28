"""Создание aiogram Bot и Dispatcher + запуск (polling/webhook).

Этап 1 — заглушка: объекты создаются, хендлеров нет. Реальные команды и
уведомления — этап 5. Режим webhook/polling — ARCHITECTURE §10 Q-A4.
"""
from __future__ import annotations

import asyncio
from typing import Optional

import structlog
from aiogram import Bot, Dispatcher

from app.config import Settings

log = structlog.get_logger()

# Глобальные объекты бота (создаются в lifespan, используются в роутах).
bot: Optional[Bot] = None
dispatcher: Optional[Dispatcher] = None
_polling_task: Optional[asyncio.Task] = None


def init_bot(settings: Settings) -> tuple[Bot, Dispatcher]:
    """Создаёт Bot и Dispatcher. Возвращает их для использования в lifespan/роутах.

    На этапе 1 токен может быть пустым (dev) — тогда бот не инициализируется.
    """
    global bot, dispatcher
    if not settings.telegram_bot_token or settings.telegram_bot_token.startswith("0000"):
        log.warning("bot.skip_no_token")
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан — бот не запускается (этап 1: это нормально)")

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()
    # TODO(этап 5): зарегистрировать роутеры/хендлеры команд и сообщений.
    log.info("bot.initialized", mode=settings.bot_mode)
    return bot, dispatcher


async def start_bot(settings: Settings) -> None:
    """Запускает бот согласно BOT_MODE (Q-A4).

    - polling: фоновая asyncio-таска (для локального dev).
    - webhook: на этапе 1 не поднимаем (роут /bot/webhook добавится в этапе 5).
    """
    global _polling_task
    if bot is None or dispatcher is None:
        return  # бот не инициализирован (нет токена) — это нормально для этапа 1

    if settings.bot_mode == "polling":
        _polling_task = asyncio.create_task(_run_polling())
        log.info("bot.polling_started")
    else:
        # TODO(этап 5): установить вебхук через bot.set_webhook(bot_webhook_url).
        log.info("bot.webhook_mode_placeholder")


async def stop_bot() -> None:
    """Корректно останавливает бот (вызывается в lifespan shutdown)."""
    global _polling_task, bot
    if _polling_task is not None:
        _polling_task.cancel()
        try:
            await _polling_task
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # noqa: BLE001
            # Таска могла упасть раньше (напр. отозванный токен → TelegramUnauthorizedError).
            # Не пробрасываем: иначе shutdown в lifespan прервётся и watcher не остановится.
            log.error("bot.polling_failed", error=str(exc))
        _polling_task = None
    if bot is not None:
        await bot.session.close()
    log.info("bot.stopped")


async def _run_polling() -> None:
    """Фоновая таска long-polling (для dev).

    handle_signals=False: иначе aiogram через loop.add_signal_handler перехватывает
    SIGINT/SIGTERM у uvicorn — по сигналу останавливается только polling, а сервер
    продолжает работать и lifespan shutdown не выполняется.
    """
    assert dispatcher is not None and bot is not None
    await dispatcher.start_polling(bot, handle_signals=False)
