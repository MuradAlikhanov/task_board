"""Конфигурация приложения.

Единственное место чтения настроек окружения — `get_settings()`.
См. ARCHITECTURE §6, .env.example. Никаких os.getenv в прикладном коде.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки из окружения (см. .env.example)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === Окружение ===
    app_env: Literal["development", "production"] = Field(
        default="development", description="development | production"
    )
    domain: str = Field(default="localhost", description="Публичный домен сервиса")

    # === Пути ===
    vault_path: Path = Field(default=Path("/app/vault"), description="Путь к vault")
    db_path: Path = Field(
        default=Path("/app/db/index.sqlite"),
        description="Путь к SQLite-индексу (вне vault, ARCHITECTURE §7)",
    )

    # === Авторизация (этап 2) ===
    jwt_secret: str = Field(default="change-me", description="Секрет подписи JWT")
    jwt_access_ttl_minutes: int = 30
    jwt_refresh_ttl_days: int = 14
    dev_auth_token: str | None = Field(
        default=None,
        description=(
            "Статический токен для локальной отладки без Telegram Login. "
            "Работает ТОЛЬКО при app_env != production (ARCHITECTURE §6.2)."
        ),
    )

    # === Telegram-бот ===
    telegram_bot_token: str = Field(default="", description="Токен от @BotFather")
    bot_mode: Literal["webhook", "polling"] = Field(
        default="polling", description="Режим получения апдейтов (Q-A4)"
    )
    bot_webhook_url: str | None = None

    # === Gemini API (этап 5/7) ===
    gemini_api_key: str = Field(default="", description="Google AI API key")

    # === CORS ===
    cors_origins: str = Field(
        default="http://localhost:3000,https://web.telegram.org",
        description="Разрешённые origin'ы через запятую",
    )

    # === API-ключи (этап 7) ===
    api_keys: str = Field(default="", description="Начальные API-ключи через запятую")

    # === Логирование ===
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ------------------------------------------------------------------
    # Производные свойства
    # ------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_dev(self) -> bool:
        return self.app_env == "development"

    @property
    def cors_origin_list(self) -> list[str]:
        """Список разрешённых CORS origin'ов."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def api_key_list(self) -> list[str]:
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

    # ------------------------------------------------------------------
    # Валидация cross-полей
    # ------------------------------------------------------------------
    @model_validator(mode="after")
    def _validate_prod_secrets(self) -> "Settings":
        """Безопасность production (ARCHITECTURE §6.2).

        - JWT_SECRET: дефолтный/пустой секрет в production запрещён — падаем на старте,
          иначе все токены подписаны известной строкой.
        - DEV_AUTH_TOKEN: принудительно обнуляется в production.
        """
        if self.is_production:
            if not self.jwt_secret or "change-me" in self.jwt_secret.lower():
                raise ValueError(
                    "JWT_SECRET пустой или плейсхолдер (содержит 'change-me') — "
                    "запуск в production запрещён. Сгенерируйте: openssl rand -hex 32."
                )
            if self.dev_auth_token:
                # Не падаем, но принудительно обнуляем — безопасность.
                object.__setattr__(self, "dev_auth_token", None)
        return self


@lru_cache
def get_settings() -> Settings:
    """Возвращает синглтон настроек. Использовать везде вместо прямого чтения env."""
    return Settings()
