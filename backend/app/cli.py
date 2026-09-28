"""CLI администратора (ARCHITECTURE §9).

Запуск: ``docker compose exec backend python -m app.cli <command>``.

Команды:
- ``init-vault``     — первичная инициализация дерева vault + дефолтный config.yml.
- ``init-admin``     — создать контакт первого Admin (Q-A1, bootstrap §6.2).
- ``reindex-all``    — принудительная полная переиндексация.
- ``cleanup-orphans`` — поиск/удаление осиротевших вложений (VISION §4.8).

Этап 1 — каркас команд с TODO. Реальная логика появляется в этапах 2–3.
"""
from __future__ import annotations

import typer

import structlog

from app.config import get_settings

app = typer.Typer(add_completion=False, help="Task Board admin CLI")
log = structlog.get_logger()


@app.command("init-vault")
def init_vault() -> None:
    """Создать дерево vault (tasks/, archive/, wiki/..., attachments/) + дефолтный config.yml."""
    settings = get_settings()
    # TODO(этап 2): создать недостающие каталоги, скопировать дефолтный config.yml.
    typer.echo(f"[stub] init-vault: path={settings.vault_path} — реализация в этапе 2")


@app.command("init-admin")
def init_admin(
    telegram: str = typer.Option(..., "--telegram", "-t", help="Telegram username, напр. @murad"),
    name: str = typer.Option(..., "--name", "-n", help="Имя администратора"),
) -> None:
    """Создать первый контакт-админ (bootstrap, ARCHITECTURE §6.2)."""
    # TODO(этап 2): создать wiki/contacts/<key>.md с team_member=true, system_role=admin.
    typer.echo(f"[stub] init-admin: telegram={telegram} name={name} — реализация в этапе 2")


@app.command("reindex-all")
def reindex_all() -> None:
    """Полная переиндексация vault (обход .md + пересобрать SQLite + векторы)."""
    # TODO(этап 3): обойти vault, пересобрать index.sqlite, пересчитать embeddings.
    typer.echo("[stub] reindex-all — реализация в этапе 3")


@app.command("cleanup-orphans")
def cleanup_orphans(
    older_than_days: int = typer.Option(7, "--older-than", help="Age-фильтр в днях (Q-A5/Gemini #5)"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Только отчёт, без удаления"),
) -> None:
    """Найти/удалить осиротевшие вложения старше N дней (VISION §4.8)."""
    # TODO(этап 3/6): сканировать attachments/, сопоставить со ссылками, удалить с подтверждением.
    typer.echo(
        f"[stub] cleanup-orphans: older_than_days={older_than_days} dry_run={dry_run} "
        "— реализация в этапе 3/6"
    )


if __name__ == "__main__":
    app()
