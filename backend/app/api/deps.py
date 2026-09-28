"""Зависимости FastAPI (Depends).

Этап 1 — только заглушки. Реальные зависимости (get_current_user,
get_db_session, require_admin) появятся в этапе 2 (авторизация) и 3.
"""
from __future__ import annotations

from typing import Any


async def get_current_user() -> Any:
    """Заглушка. Этап 2: JWT/Telegram-auth → контакт (VISION §2, §8, API §3)."""
    raise NotImplementedError("Auth — этап 2")
