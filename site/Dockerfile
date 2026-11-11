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
ARG PUBLIC_GISCUS_REPO=pythoninthegrass/megabonk_mods
ARG PUBLIC_GISCUS_REPO_ID=R_kgDOU-wlgA
ARG PUBLIC_GISCUS_CATEGORY=Announcements
ARG PUBLIC_GISCUS_CATEGORY_ID=DIC_kwDOU-wlgM4DKvzG
ENV PUBLIC_GISCUS_REPO=$PUBLIC_GISCUS_REPO PUBLIC_GISCUS_REPO_ID=$PUBLIC_GISCUS_REPO_ID PUBLIC_GISCUS_CATEGORY=$PUBLIC_GISCUS_CATEGORY PUBLIC_GISCUS_CATEGORY_ID=$PUBLIC_GISCUS_CATEGORY_ID
RUN --mount=type=cache,target=/app/site/node_modules/.astro,sharing=locked bun run scripts/sync-docs.mjs && NODE_ENV=production bunx --bun astro build

FROM oven/bun:1.4.4-alpine
WORKDIR /app
COPY --from=build --chown=bun:bun /app/site/dist ./dist
COPY --chown=bun:bun site/server.mjs site/smoke.mjs ./
ENV NODE_ENV=production HOST=0.0.0.0 PORT=8080
USER bun
EXPOSE 8080
CMD ["bun", "server.mjs"]
