FROM node:22-alpine AS build
WORKDIR /app/site
COPY site/package.json site/package-lock.json ./
RUN npm ci
COPY docs/ /app/docs/
COPY site/ ./
RUN npm run build

FROM node:22-alpine
WORKDIR /app
COPY --from=build --chown=node:node /app/site/dist ./dist
COPY --chown=node:node site/server.mjs site/smoke.mjs ./
ENV NODE_ENV=production HOST=0.0.0.0 PORT=8080
USER node
EXPOSE 8080
CMD ["node", "server.mjs"]
