# megabonkmod.party

Static Astro showcase for Megabonk Levels at [megabonkmod.party](https://megabonkmod.party/), with a Starlight player wiki at [docs.megabonkmod.party/home/](https://docs.megabonkmod.party/home/). Both ship in one image from [`dokploy.yml`](../dokploy.yml).

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

The build produces `dist/` with the showcase at `/`, the wiki home at `/home/` and guides under `/docs/`. Wiki canonical URLs use the docs hostname; the showcase retains its apex canonical metadata. The production server redirects the docs hostname's root and the legacy `/docs/` homepage to `/home/`.

## Wiki content

Edit the authoritative Markdown in `../docs/`, not the generated copies in `src/content/docs/`. `scripts/sync-docs.mjs` publishes an explicit eight-guide allowlist before `dev`, `check` and `build`; the dev wrapper watches `../docs/`. It turns the leading H1 into frontmatter, rewrites published-guide links to wiki URLs and other repository links to GitHub, and preserves unchanged file timestamps. Generated copies are gitignored. The wiki index is hand-authored at `src/content/docs/home.md`; navigation is curated in `astro.config.mjs`.

Starlight provides Pagefind search, sidebar navigation, section contents and code-block copying. **Search works only after a production build**, not in `npm run dev`. Use `npm run build` then `npm run preview` (or `node server.mjs`) to test search. The build explicitly sets `NODE_ENV=production` so an inherited development setting cannot disable the search UI.

Each page has Copy page and View as Markdown controls. `/<slug>.md` serves standalone guide Markdown with its title, and `/home.md` serves the index. The legacy `/docs/index.md` redirects to `/home.md`. Copy uses the raw endpoint, with a textarea fallback for plain HTTP or denied clipboard permissions. `/llms.txt`, `/llms-full.txt` and `/llms-small.txt` provide the index and combined text. No-JavaScript readers can still follow View as Markdown.

## Serving with Docker

With Docker Engine and Docker Compose v2 installed, the site builds and serves in a container without host Node or npm. The multi-stage `Dockerfile` builds and serves on Bun (`oven/bun` Alpine) with `server.mjs`; the non-root image contains only `dist/`, `server.mjs` and `smoke.mjs`. The build context is the repository root so the wiki can read `docs/`. The root `.dockerignore` allows only `docs/*.md` and site sources, excluding dependencies, output, design-review state, generated guides and `.env*` files. The `bun install` and `astro build` steps use BuildKit cache mounts for Bun's package cache and Astro's `node_modules/.astro` cache (optimized images and content), which persist on the Docker host between builds, so a rebuild reuses them instead of re-encoding the screenshots. From `site/`:

```sh
docker compose up -d --build   # build and start, then open http://127.0.0.1:8080/
docker compose ps              # status, including health
docker compose logs site       # server logs
docker compose down            # stop
```

Re-run `docker compose up -d --build` after content or server changes to rebuild. The published host port defaults to `8080` and is configurable with `SITE_PORT` (per command, or in the gitignored root `.env`; the root [`.env.example`](../.env.example) is the template and sets `COMPOSE_FILE`, which makes Compose read that `.env`): `SITE_PORT=8123 docker compose up -d`. Run these Compose commands from the repository root, not from `site/`, so the root `.env` is found. The service publishes on `127.0.0.1` only, and `smoke.mjs` — the container health check — fetches the home page and every referenced local CSS, JavaScript and image; run it on demand with `docker compose exec site bun smoke.mjs`. Container serving is the local preview path; the published site is deployed with the same image, described under Deployment.

## Deployment

The site at `megabonkmod.party` redeploys on every push to `main` that touches `site/**` or `docs/**`, through the Dokploy GitHub app; no command is needed for content changes. The Dokploy project itself is scaffolded and changed declaratively: [`dokploy.yml`](../dokploy.yml) at the repository root describes the Dokploy project, the `site` app and its domain, and the icarus CLI (`ic`) reconciles it against the control plane. Commands run from `site/` because icarus reads `.env` from the working directory, where the control plane's URL and API key live in the gitignored file; the server address itself is never committed. `ic --env prod check`, `plan`, `apply` and `status` cover the workflow, Dokploy builds `site/Dockerfile` from the pushed commit, and `bun smoke.mjs` is both the container health check and the post-deploy verification. See [Deployment](../docs/website.md#deployment) for the full setup, DNS requirements and state file.

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
