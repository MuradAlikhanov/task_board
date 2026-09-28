"use client";

import { useEffect, useState } from "react";

type BackendStatus = {
  status: string | null;
  error: string | null;
};

/**
 * Стартовая страница Task Board (заглушка этапа 1).
 *
 * Проверяет связь с backend API через прокси (NEXT_PUBLIC_API_URL).
 * Канбан/списки/карточки — этап 3.
 */
export default function Home() {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
  const [backend, setBackend] = useState<BackendStatus>({ status: null, error: null });

  useEffect(() => {
    fetch(`${apiBase}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d) => setBackend({ status: d.status || d.name || "ok", error: null }))
      .catch((e) => setBackend({ status: null, error: String(e) }));
  }, [apiBase]);

  return (
    <main style={{ padding: "2rem", maxWidth: 720, margin: "0 auto" }}>
      <h1 style={{ marginBottom: "0.25rem" }}>📋 Task Board</h1>
      <p style={{ color: "#666", marginTop: 0 }}>
        Управление сопровождением проектов малой командой.
      </p>

      <section
        style={{
          marginTop: "2rem",
          padding: "1rem 1.25rem",
          border: "1px solid #e5e7eb",
          borderRadius: 8,
          background: "#fafafa",
        }}
      >
        <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Связь с API</h2>
        {backend.error ? (
          <p style={{ color: "#b91c1c" }}>❌ Ошибка: {backend.error}</p>
        ) : backend.status ? (
          <p style={{ color: "#15803d" }}>✅ API отвечает: {backend.status}</p>
        ) : (
          <p style={{ color: "#666" }}>…проверка</p>
        )}
        <p style={{ fontSize: "0.85rem", color: "#999", marginBottom: 0 }}>
          Этап 1: фундамент. Канбан, списки и карточки появятся на этапе 3.
        </p>
      </section>
    </main>
  );
}
