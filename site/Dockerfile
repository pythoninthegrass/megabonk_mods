# syntax=docker/dockerfile:1
FROM oven/bun:1.4.4-alpine AS build
ENV ASTRO_TELEMETRY_DISABLED=1
WORKDIR /app/site
COPY site/package.json site/package-lock.json ./
RUN --mount=type=cache,target=/root/.bun/install/cache bun install --frozen-lockfile
COPY docs/ /app/docs/
COPY site/ ./
ARG PUBLIC_PB_URL=https://api.megabonkmod.party
ENV PUBLIC_PB_URL=$PUBLIC_PB_URL
RUN --mount=type=cache,target=/app/site/node_modules/.astro,sharing=locked bun run scripts/sync-docs.mjs && NODE_ENV=production bunx --bun astro build

FROM oven/bun:1.4.4-alpine
WORKDIR /app
COPY --from=build --chown=bun:bun /app/site/dist ./dist
COPY --chown=bun:bun site/server.mjs site/smoke.mjs ./
ENV NODE_ENV=production HOST=0.0.0.0 PORT=8080
USER bun
EXPOSE 8080
CMD ["bun", "server.mjs"]
