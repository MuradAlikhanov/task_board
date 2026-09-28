"""Filesystem watcher для vault (watchdog).

Этап 1 — заглушка: обработчики логируют события, реальная индексация
(парсинг frontmatter, запись в SQLite, own-write tracking) — этап 3.
Защита от echo-loop — ARCHITECTURE §4.

Обрабатываются все типы событий: Obsidian/Syncthing создают файлы (on_created),
переименовывают (on_moved — в т.ч. атомарная запись через temp-файл), удаляют
(on_deleted). Служебные файлы фильтруются (см. _is_relevant).
"""
from __future__ import annotations

from pathlib import Path

import structlog
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.config import Settings

log = structlog.get_logger()

# Каталоги/паттерны, которые не относятся к заметкам vault:
# - .taskboard/ — служебный (index.sqlite и пр.);
# - *.sync-conflict-*, .syncthing* — артефакты Syncthing;
# - .stfolder/.stignore — маркеры Syncthing;
# - *.tmp, ~* — временные файлы редакторов и атомарных записей.
_IGNORED_PARTS = {".taskboard", ".stfolder", ".obsidian", ".trash"}
_IGNORED_PREFIXES = (".syncthing", "~")
_IGNORED_SUBSTRINGS = (".sync-conflict-",)


def _is_relevant(path: str) -> bool:
    """Только .md-заметки, без служебных файлов Syncthing/редакторов."""
    p = Path(path)
    if p.suffix != ".md":
        return False
    for part in p.parts:
        if part in _IGNORED_PARTS or part.startswith(_IGNORED_PREFIXES):
            return False
    name = p.name
    return not any(s in name for s in _IGNORED_SUBSTRINGS)


class _VaultHandler(FileSystemEventHandler):
    """Обработчик событий изменения файлов vault."""

    def _handle(self, event_type: str, path: str) -> None:
        if not _is_relevant(path):
            return
        # TODO(этап 3): парсинг frontmatter → обновление SQLite.
        # Защита от echo-loop: own-write tracking (in-memory set) + etag.
        log.debug("watcher.file_event", type=event_type, path=path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._handle("modified", str(event.src_path))

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._handle("created", str(event.src_path))

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._handle("deleted", str(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        # Оба конца фильтруются независимо: перемещение в игнорируемое место
        # (удаление в Obsidian = перенос в .trash/, переименование x.md → x.txt)
        # даёт только moved_from — для индекса это удаление исходного ключа (этап 3).
        if not event.is_directory:
            self._handle("moved_from", str(event.src_path))
            self._handle("moved_to", str(event.dest_path))


def start_watcher(settings: Settings) -> Observer:
    """Запускает watcher на vault_path. Возвращает Observer (для остановки).

    Каталог vault должен существовать (проверяется в lifespan): без него поток
    эмиттера watchdog молча умрёт. Сами его не создаём — опечатка в VAULT_PATH
    должна проявиться в /ready, а не подменить vault пустым каталогом.
    """
    observer = Observer()
    observer.schedule(_VaultHandler(), str(settings.vault_path), recursive=True)
    observer.start()
    log.info("watcher.started", path=str(settings.vault_path))
    return observer


def stop_watcher(observer: Observer) -> None:
    """Останавливает watcher (с таймаутом, чтобы не подвесить shutdown)."""
    observer.stop()
    observer.join(timeout=5)
    if observer.is_alive():
        log.warning("watcher.stop_timeout")
    else:
        log.info("watcher.stopped")
