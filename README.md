# Task Board

Веб-приложение для управления сопровождением программных проектов малой командой (2–3 человека): заявки (канбан + списки), база знаний (Obsidian-first), Telegram-бот и Mini App, готовность к ИИ-агентам.

> **Статус:** Этап 1 (фундамент и контейнеризация). Документация проекта — см. раздел ниже.

---

## Документация проекта

Перед разработкой ознакомьтесь с согласованиями:

| Файл | Назначение |
|------|------------|
| [`VISION.md`](./VISION.md) | Функциональное видение (возможности, сценарии, правила). |
| [`VAULT_EXAMPLES.md`](./VAULT_EXAMPLES.md) | Шаблоны хранения: структура vault, примеры Frontmatter. |
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | Стек, компоненты, деплой, принятые архитектурные решения (Q-A1…Q-A5). |
| [`DATA_MODEL.md`](./DATA_MODEL.md) | Модели данных: vault-сущности + схема SQLite-индекса. |
| [`API.md`](./API.md) | REST/MCP эндпоинты. |

Ключевые принципы архитектуры (ARCHITECTURE §1):
- **Файлы Vault — источник правды, SQLite — производный индекс.**
- **Один компактный Python-контейнер** (FastAPI + aiogram-бот), единый SQLite-индекс.
- **Obsidian-first**: данные хранятся как Markdown + YAML и редактируются в Obsidian.

---

## Быстрый старт (Этап 1)

### Требования
- Docker и Docker Compose.
- Node.js 24+ — только для локальной разработки фронтенда (`npm run dev`). Docker собирает
  фронтенд по закоммиченному `package-lock.json` (`npm ci`).

### Запуск
```bash
# 1. Скопировать переменные окружения и заполнить .env
cp .env.example .env

# 2. Поднять сервисы
docker compose up -d --build

# 3. Проверить здоровье
# при DOMAIN=localhost Caddy отдаёт только HTTPS (внутренний CA, http:// → редирект), -k — не проверять сертификат
curl -k https://localhost/healthz   # {"status":"ok"}  — liveness
curl -k https://localhost/ready     # readiness (vault доступен, SQLite-индекс открывается)
```

После запуска:
- Веб-фронтенд: `https://localhost` (через Caddy; порты backend/frontend наружу не публикуются).
- API: `https://localhost/api/v1/`.
- Документация API (Swagger): `https://localhost/docs` (только при `APP_ENV != production`).

### Vault
Структура vault создана в репозитории (`vault/`):
- `tasks/` — активные заявки; `archive/` — архивные; `attachments/` — общая папка медиа.
- `wiki/projects|clients|contacts|regulations|knowledge/` — справочники и база знаний.
- `wiki/_secret/` — не индексируется в RAG (ARCHITECTURE §6.1).
- `.taskboard/config.yml` — дефолтная схема (статусы, приоритеты).

SQLite-индекс лежит вне vault, в `db/index.sqlite` (создаётся при первом запуске, пересобирается из файлов): Syncthing его не синхронизирует.

> Vault синхронизируется с локальным Obsidian через Syncthing (см. VISION §9, ARCHITECTURE §7).

---

## Стек

| Слой | Технология |
|------|------------|
| Backend | FastAPI (Python 3.14) + aiogram 3.x |
| Frontend | Next.js 16 (App Router, React 19) |
| БД/индекс | SQLite (WAL) + FTS5 + sqlite-vec |
| Proxy/TLS | Caddy 2 |
| Контейнеры | Docker / Docker Compose |
| Синхронизация vault | Syncthing |
| ИИ | Gemini API (embedding, транскрипция) — этап 5/7 |

Подробнее с обоснованием выбора — в [`ARCHITECTURE.md`](./ARCHITECTURE.md §2).

---

## Структура репозитория

```
task_board/
├── docker-compose.yml      # сервисы: proxy, backend, frontend
├── .env.example            # переменные окружения
├── backend/                # FastAPI + aiogram (app/ с модульной структурой)
├── frontend/               # Next.js (веб + TMA)
├── proxy/                  # Caddyfile
├── vault/                  # Obsidian-vault (источник правды)
└── *.md                    # документация проекта
```

---

## Roadmap

Текущий прогресс по этапам (VISION §13):

- [x] **Этап 1.** Фундамент и контейнеризация (этот коммит).
- [ ] **Этап 2.** Авторизация (Telegram Login, Telegram initData, роли Admin/Member).
- [ ] **Этап 3.** Ядро заявок и Wiki (индексация vault, канбан, списки, custom-поля, архив).
- [ ] **Этап 4.** Дашборд и отчёты.
- [ ] **Этап 5.** Telegram-бот и Mini App.
- [ ] **Этап 6.** Расширения (saved views, комментарии, темы).
- [ ] **Этап 7.** ИИ (MCP API, RAG, ассистент) и деплой на VPS.

Ревью проекта после этапа 1 (30.09.2026): недоделки этапа 1, решения до начала этапа 2 и чек-лист следующих шагов —
[«Ревью проекта Task Board»](https://claude.ai/artifact/7mPuwkL1FSqBreE2rxMEM7) (приватный документ, открывается из аккаунта владельца).
