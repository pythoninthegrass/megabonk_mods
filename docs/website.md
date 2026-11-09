# Website development

The creator-first showcase for **megabonkmod.party** lives in [`site/`](../site/README.md). It is a single-page, static Astro site explaining the level editor, console and MCP tools through original Bramblecrown Hill captures, command examples and links to the maintained guides.

The website is separate from the game mod: it neither connects to the running game nor exposes the development harness. Website-only changes do not need `task mod:build`, a game launch or a mod relaunch.

## Stack and design

- **Astro** renders the page and Markdown at build time, with static output and responsive image optimization.
- **Markdown** holds section prose, setup instructions and formatted command examples; keep content there rather than moving it into client-side code.
- **Vanilla JavaScript** progressively adds clipboard buttons, including manual-copy guidance if access is unavailable or denied.
- **Alpine.js** changes which build/play screenshot is emphasized. Both images remain visible; mobile stacks them, and the page remains readable without JavaScript.
- **Basecoat UI** supplies control styling over Tailwind CSS. Load Basecoat after Tailwind; the current buttons and native setup disclosure need no Basecoat JavaScript bundle.

The visual direction is **Build table**: pale blue working surfaces, graphite text, paper-backed screenshots and vermilion actions. See [`site/PRODUCT.md`](../site/PRODUCT.md) for product constraints, [`site/DESIGN.md`](../site/DESIGN.md) for the shipped design system and [the surface brief](../site/.impeccable/surfaces/src-pages-index-astro.md) for page-specific composition and behavior. These website rules do not prescribe the in-game editor's styling.

### Design context location

The website is its own Impeccable project root: `PRODUCT.md`, `DESIGN.md` and `.impeccable/` all live under `site/`, rather than applying to the game-mod repository as a whole. Run Impeccable from `site/`, or supply `--target site` from the repository root when the command supports it. The shared skill installation stays under the repository's `.agents/skills/impeccable/`.

For example, load context for the page from the repository root with:

```sh
.agents/skills/impeccable/scripts/impeccable context --target site/src/pages/index.astro
```

Surface-brief targets and design-system source paths are relative to `site/`, such as `src/pages/index.astro`, not `site/src/pages/index.astro`. Commit the product and design documents, `site/.impeccable/config.json`, `site/.impeccable/design.json` and the surface briefs; the runtime directories retain their own ignore files for local screenshots, mocks and question state.

## Local development

Use Node.js 22.12 or newer and the committed npm lockfile. From the repository root:

```sh
cd site
npm ci
npm run dev
```

Open the URL Astro prints, normally `http://127.0.0.1:4321/`. The npm scripts bind to loopback by default. If Astro reports a detached development server, stop it from `site/` with:

```sh
npm exec astro dev stop
```

## Container serving

Docker Engine with Docker Compose v2 is the only prerequisite: the image builds the site from source inside the container, so the host needs no Node, npm or game tooling for this workflow. The container tooling lives with the site: `site/Dockerfile`, `site/docker-compose.yml`, `site/.dockerignore`, plus the dependency-free static server `site/server.mjs` and the smoke check `site/smoke.mjs`. The multi-stage Dockerfile runs `npm ci` and `astro build` in a Node 22 Alpine build stage, then serves `dist/` from a slim stage that contains only `dist/`, `server.mjs` and `smoke.mjs` and runs as a non-root user. The build context is `site/`, so game and mod assets never enter it, and `site/.dockerignore` additionally keeps out `node_modules/`, `.astro/`, `dist/`, the `.impeccable/` design-review state, `.env*` files and logs.

From the repository root:

```sh
docker compose -f site/docker-compose.yml up -d --build   # build and start
docker compose -f site/docker-compose.yml ps              # status, including health
docker compose -f site/docker-compose.yml logs site       # server logs
docker compose -f site/docker-compose.yml down            # stop
```

Open `http://127.0.0.1:8080/`. The published host port defaults to `8080` and is configurable through `SITE_PORT`, either per command (`SITE_PORT=8123 docker compose -f site/docker-compose.yml up -d`) or in a gitignored `site/.env` file that Compose reads automatically; [`site/.env.example`](../site/.env.example) is the template for both that variable and the deployment settings below. Rebuild after editing content, the server or the image itself with `up -d --build`. The service publishes on `127.0.0.1` only, serves the static files with content types and cache headers (immutable for hashed `_astro/` assets, revalidation for `index.html`), and runs `node smoke.mjs` as its health check; `ps` reports `healthy` once it passes. To run that smoke check by hand, which fetches the home page and every local CSS, JavaScript and image it references and asserts status and content type:

```sh
docker compose -f site/docker-compose.yml exec site node smoke.mjs
```

The same checks run on the host as part of `npm run test:site`. Compose is the local preview path; the published site is deployed by Dokploy under Deployment.

## Source map

Paths below are relative to the repository root.

| Path | Purpose |
| --- | --- |
| `site/src/pages/index.astro` | Single page, navigation, metadata, section composition and browser enhancements |
| `site/src/content/*.md` | Section copy, instructions and syntax-highlighted command examples |
| `site/src/components/` | Shared command blocks, video placeholders and SVG icons |
| `site/src/styles/global.css` | Basecoat imports and overrides, site tokens, layout, responsive rules and reduced-motion fallback |
| `site/src/scripts/clipboard.js` | Testable clipboard behavior |
| `site/src/assets/` | Original game captures that Astro turns into responsive WebP variants |
| `site/public/` | Unprocessed public files, including the favicon, social image and robots rules |
| `site/astro.config.mjs` | Canonical site URL, static output, Tailwind integration and Markdown highlighting |
| `site/tests/` | Clipboard unit tests and assertions against the generated page |
| `site/server.mjs` | Dependency-free static server used by the container and the built-output serve tests |
| `site/smoke.mjs` | Smoke check of the home page and every local CSS, JavaScript and image it references |
| `site/Dockerfile`, `site/docker-compose.yml`, `site/.dockerignore` | Multi-stage container build and local Compose serving, described under Container serving |
| `site/.env.example` | Template for the gitignored `site/.env`: Compose port plus the Dokploy CLI credentials |
| `dokploy.yml` | Declarative Dokploy deployment config for the published site, applied with the `ic` CLI under Deployment |

Keep `site/package.json` and `site/package-lock.json` together when changing dependencies. `site/node_modules/`, `site/.astro/` and `site/dist/` are generated and ignored by Git.

## Links and content accuracy

All off-site anchors use `target="_blank"` and `rel="noopener noreferrer"`; internal section links stay in the current tab. In `index.astro`, spread the shared `external` attributes onto external anchors. Markdown has no standard target attribute, so use an HTML anchor for an off-site link:

```html
<a href="https://thunderstore.io/c/megabonk/p/BepInEx/BepInExPack_IL2CPP/" target="_blank" rel="noopener noreferrer">BepInEx 6 IL2CPP</a>
```

The built-page link test covers both Astro and Markdown content. Inline prose links are underlined.

The [player guide](player-guide.md), [modding setup](modding-setup.md), [starter-level guide](starter-level.md) and [development harness guide](development.md) remain authoritative for game behavior. Keep website claims synchronized with them:

- Do not imply that a public installer download or Steam Workshop subscription exists when it does not.
- Distinguish the supported Windows game build under Proton or Wine from native Linux/macOS support.
- Preserve map-specific terrain-editing limits and distinguish cheat/debug permissions from enabling the development harness.
- Label in-game console commands, shell commands and illustrative MCP tool calls separately.

## Screenshots and videos

The `bramblecrown-editor.png`, `bramblecrown-gameplay.png` and `bramblecrown-console.png` assets are actual in-game captures, with their origin recorded in embedded metadata. The gameplay camera was positioned while the run was frozen; that image is not evidence of playability or performance. The starter's selection illustration is artwork, not a gameplay screenshot.

Use the [screenshot workflow](development.md#retaining-screenshots) to obtain replacement captures, preserve meaningful alt text and independent captions, and avoid overwriting unsaved level work while preparing a shot. Inspect the images themselves before publishing; do not substitute generated UI for actual game evidence. Game imagery remains the property of its respective rights holders.

`site/public/social.jpg` is a 1200 × 630 crop of the gameplay capture. Update it alongside showcase changes; files in `public/` are copied as-is rather than optimized by Astro.

There are two intentionally unplayable video placeholders: the editor workflow and the gameplay tour. Until recordings exist, retain their real posters and “Video coming soon” labels without fake play controls. To publish a recording, replace the corresponding `VideoPlaceholder` in `index.astro` with native video markup using `controls`, `playsinline`, `preload="none"` and a poster; add captions and an instructional transcript where appropriate. Do not add autoplay or third-party embeds by default.

## Validation

From `site/`, run:

```sh
npm run check
npm test
npm run build
npm run test:site
npm audit
npm run preview
```

`test:site` reads `dist/index.html`, so build first. It checks static content, local assets, video placeholders, fragment destinations, setup claims and safe new-tab behavior for external links. It also serves `dist/` through `server.mjs` and runs the container smoke checks, asserting the home page plus every referenced local CSS, JavaScript and image answer with the right status and content type. `npm test` checks exact clipboard text and unavailable/denied clipboard behavior. The production preview serves the built files, not the development source; rebuild after edits before reviewing it.

From the repository root, `task lint` checks Markdown and Python lint. The Markdown ignore file excludes website dependencies, generated files and embedded content fragments, whose heading levels and sentence-style headings belong to the surrounding page. The repository's `task check` also builds/deploys the game mod and runs unrelated suites; it does not replace the website checks above.

Review desktop and mobile layouts in a real browser, including both screenshot emphasis states, copy feedback, keyboard focus and the expanded MCP configuration. Long configuration lines must scroll inside their block rather than widen the page. Check that all images load before full-page screenshots, that reduced motion is respected and that content and native disclosures remain usable without JavaScript.

## Deployment

`npm run build` produces `site/dist/`, suitable for a static host at the domain root; the site is published at `https://megabonkmod.party/`. Deployment is declarative: `dokploy.yml` at the repository root describes the project, the single `site` app and its domain, and the [icarus](https://github.com/pythoninthegrass/icarus) CLI (`ic`) reconciles that file against a self-hosted Dokploy control plane through its API. The control plane's address, API key and SSH target are the only hosting details that live outside the repository, in a gitignored `site/.env` copied from [`site/.env.example`](../site/.env.example) (`DOKPLOY_URL`, `DOKPLOY_API_KEY`, `DOKPLOY_ENV`, `DOKPLOY_SSH_*`); `site/.dockerignore` keeps that file out of the image and the Compose build context, and the credentials configure the CLI only — `dokploy.yml` sets `create_env_file: false`, so nothing from it is pushed into the container. Icarus reads `.env` from the working directory and locates `dokploy.yml` by walking up, so run every `ic` command from `site/`:

```sh
cd site
ic --env prod check         # credentials, reachability and config validity
ic --env prod plan          # diff against the server without writing
ic --env prod apply         # check, setup, push env, deploy in wave order
ic --env prod status        # build and deploy status per app
ic --env prod logs site     # container logs, over SSH
```

Install the CLI once from a checkout of icarus (`uv tool install <icarus checkout>`). What the config provisions:

| Piece | Value |
| --- | --- |
| Project | `megabonkmod-party`, containing the one `site` app |
| Source | GitHub `main`; Dokploy clones the repository and builds `site/Dockerfile` with the `site/` build context, so the published image is the one the local Compose file builds |
| Domain | `megabonkmod.party` routed to container port `8080`, HTTPS with a Let's Encrypt certificate; `www.megabonkmod.party` has its own router, certificate and a redirect to the apex |
| Health check | `node smoke.mjs` inside the container, the same check the Compose healthcheck runs |
| Auto-deploy | a push to `main` that touches `site/**` |

Because Dokploy builds from the pushed commit, content reaches the site only after it is committed and pushed; `ic --env prod trigger` re-runs a deploy on demand. `.dokploy-state/prod.json` maps the config's names to Dokploy's resource ids and is gitignored: `ic --env prod import` regenerates it from an existing project, and it must be present before `apply`, which otherwise creates a duplicate project. Verify a deploy from anywhere with the container's own smoke check:

```sh
curl -sI https://megabonkmod.party/          # 200, text/html
node smoke.mjs https://megabonkmod.party/    # exit 0 when every referenced asset serves
```

Both hosts' DNS is managed by DNSControl in the infrastructure repo's `dns/records/dnsconfig.js`, not in this repository. The apex and `www` are A records under `CF_PROXY_DEFAULT_OFF`, so each resolves directly to the host with no CDN proxy — otherwise the Let's Encrypt HTTP-01 challenge cannot complete. `www.megabonkmod.party` has its own router and Let's Encrypt certificate in `dokploy.yml`, plus a Traefik `redirectRegex` that sends it to the apex at HTTP 308 with the path preserved. DNSControl changes follow the usual preview-then-push loop against the `cloudflare` provider: `dnscontrol preview --domains megabonkmod.party` reports `0 corrections` when the zone matches the config, which is the check to run before a `push`.

The canonical URL appears in `site/astro.config.mjs` and the page's metadata, including social-image URLs. Keep those values consistent if the domain changes. Build and publish the static output; no Node server, game installation or harness endpoint is needed in production beyond the dependency-free static server in the image.

## Documentation references

Use these exact Context7 library IDs for current framework and component documentation:

- `/withastro/astro`
- `/websites/alpinejs_dev`
- `/hunvreus/basecoat`
