"""Background-задачи (воркеры).

Гибрид: BackgroundTasks FastAPI (I/O-bound) + run_in_executor/threadpool (CPU-bound).
См. ARCHITECTURE §3.5, §10 Q-A5. Реальные задачи (переиндексация, Gemini, PDF,
рассылка) — этапы 3–7.
"""
