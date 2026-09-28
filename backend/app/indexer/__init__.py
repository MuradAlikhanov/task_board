"""Vault Watcher + Indexer.

Подписка на изменения файлов vault, парсинг frontmatter, обновление SQLite-индекса.
См. ARCHITECTURE §4 (двухслойная защита от echo-loop: own-write tracking + etag),
DATA_MODEL §3. Реализация — этап 3.
"""
