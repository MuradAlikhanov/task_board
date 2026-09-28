"""In-memory шина событий на asyncio.Queue (ARCHITECTURE §10 Q-A1).

Один процесс → подписка через очередь. Несколько подписчиков — fan-out.
Этап 1 — заглушка интерфейса; реальное использование — этап 3+.

Пример (этап 3):
    bus = EventBus()
    await bus.publish(TaskCreated(id="TB-0001"))
    async for event in bus.subscribe(): ...
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator

import structlog

log = structlog.get_logger()


@dataclass
class Event:
    """Базовый класс события. Конкретные подклассы — в app/domain."""

    type: str


class EventBus:
    """Простая fan-out шина: каждый подписчик получает все события.

    Не предназначена для персистентности (это in-memory). При рестарте
    неподтверждённые события теряются — для домена это приемлемо (Q-A1).

    Очереди подписчиков ограничены (_MAX_QUEUE): медленный/зависший подписчик
    не копит события в RAM бесконечно и не блокирует publish — при переполнении
    событие дропается с warning (шина best-effort: потерять уведомление
    допустимо, заблокировать API-запрос — нет).
    """

    _MAX_QUEUE = 256

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[Any]] = []

    def subscribe(self) -> AsyncIterator[Any]:
        """Возвращает async-итератор событий. Создаёт свою очередь.

        Очередь регистрируется при первой итерации, а не при вызове subscribe():
        finally генератора выполняется, только если генератор был запущен, —
        иначе незапущенный подписчик навсегда остался бы в _subscribers и
        переполнялся. События, опубликованные до первой итерации, не доставляются.
        """

        async def _gen() -> AsyncIterator[Any]:
            queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=self._MAX_QUEUE)
            self._subscribers.append(queue)
            try:
                while True:
                    item = await queue.get()
                    yield item
            finally:
                self._subscribers.remove(queue)

        return _gen()

    async def publish(self, event: Any) -> None:
        """Разослать event всем подписчикам (fan-out).

        put_nowait: один медленный подписчик не блокирует остальных.
        """
        log.debug("event.published", type=getattr(event, "type", type(event).__name__))
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                log.warning(
                    "event.dropped_slow_subscriber",
                    type=getattr(event, "type", type(event).__name__),
                    queue_size=self._MAX_QUEUE,
                )


# Глобальный инстанс шины (создаётся в lifespan).
_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Возвращает синглтон шины событий."""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
