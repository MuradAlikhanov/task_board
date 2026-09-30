# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Task Board is a support-ticket/kanban + knowledge-base app for a 2–3 person team, with Telegram bot/Mini App and AI-agent access planned. The repo is at **Stage 1 (foundation/containerization)**: most backend modules are stubs with `TODO(этап N)` markers indicating which roadmap stage (README "Roadmap", VISION §13) implements them. Don't implement a later stage's feature unless asked; keep the stubs' stage markers accurate.

The design docs (all in Russian) are the spec and are cited throughout the code as `ARCHITECTURE §N`, `VISION §N`, `DATA_MODEL §N`, `API.md §N`, and decision IDs like `Q-A1`…`Q-A5` (architecture), `Q-D*` (data), `Q-P*` (API). Read the referenced section before changing behavior in that area:
- `VISION.md` — functional requirements and roadmap stages
- `ARCHITECTURE.md` — stack, components, vault↔index sync, auth, accepted decisions (§10)
- `DATA_MODEL.md` — vault entities + SQLite index schema (tables, FTS5, sqlite-vec)
- `API.md` — REST/MCP endpoints and conventions
- `VAULT_EXAMPLES.md` — vault layout and frontmatter examples

Code comments, docstrings, docs and user-facing strings are in Russian; follow that convention.

## Commands

No test suite exists yet. The frontend has ESLint (flat config, `frontend/eslint.config.mjs`) and a committed `package-lock.json`.

```bash
# Full stack (Caddy proxy + backend + frontend)
cp .env.example .env
docker compose up -d --build
docker compose logs -f backend
# DOMAIN=localhost → Caddy serves HTTPS only (internal CA, http:// redirects); -k skips cert check
curl -k https://localhost/healthz    # liveness
curl -k https://localhost/ready      # readiness: vault dir exists + index opens read-only (503 otherwise)

# Admin CLI (typer) — stubs until stages 2–3
docker compose exec backend python -m app.cli --help
docker compose exec backend python -m app.cli init-admin --telegram @user --name "Имя"

# Frontend (Next.js 16 App Router, Node 24)
cd frontend && npm install && npm run dev    # :3000; also: npm run build, npm run lint
```

Running the backend locally without Docker: dependencies are installed into `.deps/` (pip `--target` from `backend/requirements.txt`, Python 3.14 — same interpreter and pins as the Docker image). `.venv/` is an empty venv used only for the interpreter:

```bash
cd backend
PYTHONPATH=../.deps VAULT_PATH=../vault DB_PATH=../db/index.sqlite \
  ../.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

`Settings` reads `.env` relative to the current working directory, so from `backend/` the root `.env` isn't picked up — pass env vars explicitly. Defaults point at `/app/vault` and `/app/db` (container paths).

## Architecture

Three containers (`docker-compose.yml`): **Caddy** (`proxy/Caddyfile`) routes `/api/*`, `/docs`, `/redoc`, `/openapi.json`, `/bot/*`, `/healthz`, `/ready` to `backend:8000` and everything else to `frontend:3000`. It also sets CSP `frame-ancestors https://web.telegram.org` so the Telegram Mini App can render in an iframe; don't add `X-Frame-Options` (ARCHITECTURE §6.3). Frontend and backend ports are only `expose`d, so everything goes through Caddy on 80/443.

### Core invariant: vault files are the source of truth
- All data lives as Markdown + YAML frontmatter in `vault/` (edited in Obsidian and synced via Syncthing). `db/index.sqlite` (outside the vault, so Syncthing doesn't sync it) is a **derived** index that can always be rebuilt from the files. Never write to SQLite bypassing the files.
- Reads go to SQLite. Writes serialize to `.md` → the watchdog watcher (`app/indexer/watcher.py`) picks up the change → reindexes. Echo-loop protection (ARCHITECTURE §4) is two-layer: an in-memory own-write set with ~1–2s TTL, plus `etag` comparison.
- `vault/.taskboard/config.yml` holds only the schema (statuses, priorities, custom fields). Projects, clients and contacts are wiki pages under `vault/wiki/*/`, not config.
- Tasks whose status has type `archive` are moved from `tasks/` to `archive/`.
- RAG/Gemini embedding is whitelist-only: only pages with `rag: true` frontmatter. `wiki/_secret/` and `sensitive: true` pages never leave the vault (ARCHITECTURE §6.1).
- Vault content is gitignored (only `.gitkeep` and `config.yml` are tracked). The backend runs as the host `UID:GID` so Syncthing can overwrite files it creates.

### Backend: single process (decision Q-A1)
`backend/app/main.py` `lifespan` starts everything in the one FastAPI/uvicorn process: event bus → `ensure_dirs()` → vault watcher → aiogram bot, and shuts them down in reverse order. Consequences:
- **Single SQLite writer.** Use `app/db/connection.py` `connect()` for every connection (WAL, `busy_timeout`, `foreign_keys`, and per-connection sqlite-vec loading; extensions are per-connection, so never cache "loaded" globally). Lifespan creates the index once (`init_db()`), and only if the vault dir exists; nothing creates the vault itself, so a wrong `VAULT_PATH` surfaces as 503 on `/ready`. `check_db_ready()` (used by `/ready`) opens the index read-only without sqlite-vec and runs in the threadpool, so probes never create files in the synced vault.
- **Event bus** (`app/events/bus.py`): in-memory `asyncio.Queue` fan-out, no Redis. It's best-effort: bounded queues, and events are dropped (with a warning) when a subscriber is slow, so `publish` never blocks a request. The domain publishes events and the bot subscribes to send notifications.
- **Bot** runs as an asyncio task. `BOT_MODE=polling` for dev; `webhook` for prod via `/bot/webhook` (Q-A4). With no or placeholder `TELEGRAM_BOT_TOKEN`, `init_bot` raises `RuntimeError` and lifespan skips the bot; this is expected in dev.
- **Background work** (Q-A5): FastAPI `BackgroundTasks` for I/O-bound work, `run_in_executor` for CPU-bound work (PDF). No Celery.
- Module layout (`api/`, `bot/`, `domain/`, `events/`, `indexer/`, `workers/`) is deliberately split so the bot/workers can later move to separate containers.

### Config
`app/config.py` `get_settings()` (cached pydantic-settings) is the only place env vars are read. No `os.getenv` in application code. In `APP_ENV=production`, the validator refuses to start with an empty `JWT_SECRET` or one containing `change-me`, force-clears `DEV_AUTH_TOKEN`, and disables `/docs`, `/redoc` and openapi.

### API conventions (API.md §1)
REST under `/api/v1`. Auth is Bearer JWT (Telegram Login for web, `initData` for the Mini App) or `X-API-Key` for AI agents. Errors use the shape `{"error": {"code", "message", "details"}}`. Pagination is `?page=&size=` (default 50) and sorting is `?sort=field,asc|desc`. Mutations accept an `Idempotency-Key` header.

### Frontend
Next.js 16 App Router (React 19), one codebase for web and Telegram Mini App. `NEXT_PUBLIC_API_URL` (default `/api/v1`) is inlined at **build time** via the Docker build arg, so changing it requires a rebuild. `output: "standalone"` is required by the frontend Dockerfile.
