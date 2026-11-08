# megabonkmod.party

Single-page, static Astro showcase for Megabonk Levels. Hosting is intentionally undecided; nothing in this project deploys the site or changes DNS.

See [Website development](../docs/website.md) for the full workflow. Website design context lives alongside this file in [`PRODUCT.md`](PRODUCT.md), [`DESIGN.md`](DESIGN.md) and `.impeccable/`; run Impeccable from `site/` or target the site explicitly from the repository root.

## Local development

Use Node 22.12 or newer. From `site/`:

```sh
npm ci
npm run dev
```

Open the URL printed by Astro. To validate the production output:

```sh
npm run check
npm test
npm run build
npm run test:site
npm run preview
```

The build produces `dist/`, suitable for a static host at the domain root. The canonical URL is set in `astro.config.mjs` and page metadata. Configure the custom domain and HTTPS at the chosen host before launch.

## Serving with Docker

With Docker Engine and Docker Compose v2 installed, the site builds and serves in a container without host Node or npm. The multi-stage `Dockerfile` builds `dist/` on Node 22 Alpine, then serves it with the dependency-free static server in `server.mjs`; the image contains only `dist/`, `server.mjs` and `smoke.mjs`, runs as a non-root user, and the `site/`-scoped build context with `.dockerignore` excludes `node_modules/`, `.astro/`, `dist/`, the `.impeccable/` design-review state and `.env*` files. From `site/`:

```sh
docker compose up -d --build   # build and start, then open http://127.0.0.1:8080/
docker compose ps              # status, including health
docker compose logs site       # server logs
docker compose down            # stop
```

Re-run `docker compose up -d --build` after content or server changes to rebuild. The published host port defaults to `8080` and is configurable with `SITE_PORT` (per command, or in a gitignored `site/.env` that Compose reads): `SITE_PORT=8123 docker compose up -d`. The service publishes on `127.0.0.1` only, and `smoke.mjs` — the container health check — fetches the home page and every referenced local CSS, JavaScript and image; run it on demand with `docker compose exec site node smoke.mjs`. Container serving is a local preview; public hosting and DNS remain undecided.

## Editing content

- `src/content/*.md`: prose, setup instructions and syntax-highlighted command examples. These render at build time, not in the browser.
- `src/pages/index.astro`: page order, navigation, media, metadata and minimal enhancement scripts.
- `src/components/`: reusable command and media blocks.
- `src/styles/global.css`: the Build table theme, responsive rules and Basecoat token overrides.

Off-site links open in a new tab with `rel="noopener noreferrer"`. Astro links use the shared `external` attributes. In Markdown fragments, use an HTML anchor to provide these attributes without adding a Markdown plugin. The built-page test checks every link, including Markdown content; same-site navigation stays in the current tab.

Astro renders the whole page statically. Vanilla JavaScript adds clipboard controls only when available. Alpine changes which comparison image is emphasized; both remain visible, including without JavaScript. On mobile the images stack and the selected view gains an outline. Native `<details>` exposes MCP setup without a runtime. Basecoat styles buttons and the disclosure; its JavaScript bundle is not needed for the components used here.

## Screenshots and video slots

`src/assets/bramblecrown-{editor,gameplay,console}.png` are actual captures from the original Bramblecrown Hill level. They are not generated mockups. The gameplay view was captured with the run frozen and a positioned camera; it does not establish playability or performance. The editor view shows the summit, not every terrain tool in action. Embedded file metadata records their origin. Game imagery remains the property of its respective rights holders.

Astro creates responsive WebP variants. Keep meaningful alt text and captions when replacing captures. `public/social.jpg` is a 1200 × 630 crop of the gameplay capture; regenerate it when changing the showcase.

There are two intentional video placeholders: editor workflow and gameplay tour. They use real posters, say “Video coming soon”, and have no pretend play controls. To publish recordings, replace the corresponding `VideoPlaceholder` instances with native `<video controls playsinline preload="none" poster="…">`, include a source, captions where relevant, and a transcript for instructional narration. Do not add autoplay or third-party video embeds by default.

## Content accuracy

The maintained guides under `../docs/` are authoritative. Keep the public-release status, map editing limits, compatibility notes and dev/harness prerequisites synchronized with them. A public installer link should only replace the development notice once a real release exists. MCP examples are illustrative tool calls, not shell commands or a live browser connection.
