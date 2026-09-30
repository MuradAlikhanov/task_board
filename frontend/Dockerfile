# syntax=docker/dockerfile:1
# === Task Board frontend: Next.js 16 (App Router) ===
# Node.js 24 LTS (поддержка до 30.04.2028). Multi-stage: deps → build → runner.
# output: "standalone" (next.config.js) — в runner копируем только
# .next/standalone + .next/static + public (~80 МБ вместо ~400 МБ node_modules).

# --- deps: установка зависимостей ---
FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
# npm ci — строго по lockfile (воспроизводимые сборки).
RUN npm ci

# --- build: сборка production-артефакта ---
FROM node:24-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEXT_PUBLIC_* инлайнятся в клиентский бандл при сборке — значение передаётся
# через build args (docker-compose.yml: build.args), runtime environment их
# уже НЕ переопределит.
ARG NEXT_PUBLIC_API_URL=/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# --- runner: минимальный образ для запуска ---
FROM node:24-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# standalone-сервер + статика + публичные файлы (static и public НЕ входят
# в standalone-бандл — копируем отдельно).
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]
