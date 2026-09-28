"""Health-эндпоинты: /healthz и /ready.

См. ARCHITECTURE §7, §8 и VISION §13 (этап 1).
- /healthz — liveness: процесс жив (всегда 200, если uvicorn отвечает).
- /ready   — readiness: vault доступен и SQLite открывается.
"""
from __future__ import annotations

from pathlib import Path

import structlog
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.db.connection import check_db_ready

router = APIRouter(tags=["health"])
log = structlog.get_logger()


@router.get("/healthz", summary="Liveness probe")
async def healthz() -> dict[str, str]:
    """Процесс жив. Используется Docker HEALTHCHECK (см. docker-compose.yml)."""
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe")
async def ready() -> JSONResponse:
    """Готов к трафику: vault существует и доступен, SQLite открывается.

    Возвращает 200 при готовности, 503 при неготовности (без падения процесса,
    чтобы оркестратор мог дождаться восстановления).
    """
    settings = get_settings()
    checks: dict[str, str] = {}

    # 1. Vault-каталог существует и доступен.
    vault_ok = Path(settings.vault_path).is_dir()
    checks["vault"] = "ok" if vault_ok else "missing"

    # 2. SQLite открывается (этап 1 — заглушка реальной схемы). sqlite3 блокирующий
    # (до busy_timeout при конкурентной записи) — выносим из event loop.
    db_ok = await run_in_threadpool(check_db_ready)
    checks["db"] = "ok" if db_ok else "error"

    ready_all = vault_ok and db_ok
    # Пробы дёргаются часто (Docker, мониторинг) — шумим только при неготовности.
    if ready_all:
        log.debug("ready.check", checks=checks, ready=True)
    else:
        log.warning("ready.check", checks=checks, ready=False)
    return JSONResponse(
        status_code=status.HTTP_200_OK if ready_all else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"ready": ready_all, "checks": checks},
    )
