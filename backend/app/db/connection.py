"""Подключение к SQLite-индексу.
Единый источник подключений к index.sqlite. WAL + busy_timeout (см. ARCHITECTURE §10 Q-A1
— один писатель из процесса; WAL даёт конкурентное чтение). Загрузка sqlite-vec для
векторного поиска (Q-A2). Реальные таблицы создаются в этапе 3 (схема — DATA_MODEL §3).
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import structlog

from app.config import Settings, get_settings

log = structlog.get_logger()


def ensure_dirs(db_path: Path | None = None) -> Path:
    """Создаёт каталог для БД (db/, вне vault). Вызывается один раз при старте
    (lifespan) — connect() не должен мутировать файловую систему (readiness-проверки).
    """
    settings: Settings = get_settings()
    path = db_path or settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_db(db_path: Path | None = None) -> Path:
    """Создаёт каталоги и файл index.sqlite (в режиме WAL). Вызывается один раз
    при старте (lifespan): /ready открывает БД только на чтение и сам её не создаёт.
    """
    path = ensure_dirs(db_path)
    connect(path).close()
    return path


def _load_vec_extension(conn: sqlite3.Connection) -> None:
    """Загружает sqlite-vec в соединение.

    ВАЖНО: расширения SQLite загружаются на уровне КАЖДОГО соединения, а не процесса.
    Не кэшировать «загруженность» глобальным флагом — новые соединения останутся
    без vec-функций (баг, найденный на ревью). Не падает, если недоступно
    (этап 1 — заглушка).
    """
    try:
        import sqlite_vec  # type: ignore

        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        log.debug("sqlite_vec.loaded")
    except Exception as exc:  # noqa: BLE001 — на старте не хотим падать из-за vec
        log.warning("sqlite_vec.load_failed", error=str(exc))


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Создаёт новое подключение к SQLite с нужными pragma и sqlite-vec.

    Каталог БД должен существовать (см. ensure_dirs); если файл отсутствует,
    SQLite создаст его при первом обращении.
    Возвращает соединение; вызывающий обязан закрыть (или использовать `cursor()`).
    """
    settings: Settings = get_settings()
    path = db_path or settings.db_path

    # check_same_thread=False: соединение может использоваться из thread pool (Q-A5).
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # PRAGMA: WAL для конкурентного чтения; таймаут на блокировку записи.
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA foreign_keys=ON;")

    _load_vec_extension(conn)
    return conn


@contextmanager
def cursor(conn: sqlite3.Connection) -> Iterator[sqlite3.Cursor]:
    """Контекстный менеджер для курсора с коммитом/откатом."""
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def check_db_ready() -> bool:
    """Readiness-проверка: БД открывается и отвечает на простой запрос.

    Используется в /ready (ARCHITECTURE §7). Открывает БД только на чтение и без
    sqlite-vec: проверка не создаёт index.sqlite (и -wal/-shm), если его нет, —
    отсутствующий индекс означает «не готов». Блокирующая — вызывать из threadpool.
    """
    path = get_settings().db_path
    try:
        conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        try:
            conn.execute("SELECT 1;")
        finally:
            conn.close()
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("db.ready_check_failed", error=str(exc))
        return False
