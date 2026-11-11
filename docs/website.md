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

Docker Engine with Docker Compose v2 is the only prerequisite: the image builds the site from source inside the container, so the host needs no Node, npm or game tooling. The container tooling lives with the site: `site/Dockerfile`, `site/docker-compose.yml`, `site/server.mjs` and `site/smoke.mjs`, plus the repository-root `.dockerignore`. The multi-stage Dockerfile runs `bun install --frozen-lockfile` (Bun reads `package-lock.json`, so no second lockfile exists) and `astro build` on the `oven/bun` Alpine image, then serves `dist/` with Bun from a non-root stage containing only the output, server and smoke check. The repository-root context allows the wiki sync to read `docs/`; the root `.dockerignore` (Docker reads a plain `.dockerignore` only from the context root, so it cannot live under `site/`) permits only docs and site sources and excludes dependencies, generated output, `.impeccable/`, `.env*` and logs. Game and mod assets never enter the context.

From the repository root:

```sh
docker compose -f site/docker-compose.yml up -d --build   # build and start
docker compose -f site/docker-compose.yml ps              # status, including health
docker compose -f site/docker-compose.yml logs site       # server logs
docker compose -f site/docker-compose.yml down            # stop
```

Open `http://127.0.0.1:8080/`. The published host port defaults to `8080` and is configurable through `SITE_PORT`, either per command (`SITE_PORT=8123 docker compose -f site/docker-compose.yml up -d`) or in a gitignored `site/.env` file that Compose reads automatically; [`site/.env.example`](../site/.env.example) is the template for both that variable and the deployment settings below. Rebuild after editing content, the server or the image itself with `up -d --build`. The service publishes on `127.0.0.1` only, serves the static files with content types and cache headers (immutable for hashed `_astro/` assets, revalidation for `index.html`), and runs `bun smoke.mjs` as its health check; `ps` reports `healthy` once it passes. To run that smoke check by hand, which fetches the home page and every local CSS, JavaScript and image it references and asserts status and content type:

```sh
docker compose -f site/docker-compose.yml exec site bun smoke.mjs
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
| `site/src/pages/levels/`, `site/src/layouts/GalleryLayout.astro` | Gallery pages (browse, level view, upload) and their shared header and footer |
| `site/src/scripts/gallery.js`, `levels.js` | Pure, unit-tested gallery helpers: share codes, filters, dates, URLs, error text |
| `site/src/scripts/browse.js`, `level-view.js`, `upload.js`, `gallery-app.js`, `pb.js` | Alpine components, the shared sign-in store and the PocketBase client |
| `site/src/assets/` | Original game captures that Astro turns into responsive WebP variants |
| `site/public/` | Unprocessed public files, including the favicon, social image and robots rules |
| `site/astro.config.mjs` | Canonical site URL, static output, Tailwind integration and Markdown highlighting |
| `site/tests/` | Clipboard unit tests and assertions against the generated page |
| `site/server.mjs` | Dependency-free static server used by the container and the built-output serve tests |
| `site/smoke.mjs` | Smoke check of the home page and every local CSS, JavaScript and image it references |
| `site/Dockerfile`, `site/docker-compose.yml`, `.dockerignore` | Multi-stage container build and local Compose serving, described under Container serving |
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

`npm run build` produces `site/dist/`: the showcase at `/`, wiki home at `/home/` and guides at `/<slug>/`. **Content deploys on push:** Dokploy is connected to the repository through a GitHub app, and a push to `main` that touches `site/**` or `docs/**` makes it rebuild `site/Dockerfile` from the pushed commit and redeploy. Editing a guide or the site needs a commit and a push, and nothing else. The wiki pages are regenerated from `docs/` during that build, so a change to an allowlisted guide reaches the site without touching `site/`. The rest of this section covers how the Dokploy project itself is created and changed. That setup is declarative: `dokploy.yml` at the repository root describes the project, the single `site` app and its domains, and the [icarus](https://github.com/pythoninthegrass/icarus) CLI (`ic`) reconciles that file against a self-hosted Dokploy control plane through its API. The control plane's address, API key and SSH target live outside the repository in a gitignored `site/.env` copied from [`site/.env.example`](../site/.env.example) (`DOKPLOY_URL`, `DOKPLOY_API_KEY`, `DOKPLOY_ENV`, `DOKPLOY_SSH_*`). The root `.dockerignore` keeps that file out of the build context, and the credentials configure the CLI only — `dokploy.yml` sets `create_env_file: false`. Icarus reads `.env` from the working directory and locates `dokploy.yml` by walking up, so run every `ic` command from `site/`:

```sh
cd site
ic --env prod check         # credentials, reachability and config validity
ic --env prod plan          # diff against the server without writing
ic --env prod apply         # check, setup, push env, deploy in wave order
ic --env prod status        # build and deploy status per app
ic --env prod logs site     # container logs, over SSH
```

Install the CLI once from a checkout of icarus (`uv tool install <icarus checkout>`). What the config provisions:

Credentials may instead live in the gitignored repository-root `.env`: set `DOTENV_FILE=../.env` when invoking Icarus from `site/`. No `env_targets` or per-app environment is configured, so deployment credentials and game settings are not pushed into the site container.

Some Icarus versions have incomplete reconciliation for existing apps: `plan` and `apply` do not compare or save `dockerContextPath` or GitHub `watchPaths`. When changing those fields, explicitly reconcile them through `application.saveBuildType` and `application.saveGithubProvider` before triggering the deploy. Preserve the existing GitHub provider and verify the remote owner, repository and branch first. An import can also encounter a `project.all` application summary without `appName`; obtain it from `application.one` using the summary's `applicationId`, rather than creating a replacement project.

| Piece | Value |
| --- | --- |
| Project | `megabonkmod-party`, containing the one `site` app |
| Source | GitHub `main`; Dokploy builds `site/Dockerfile` with the repository-root context, restricted by the root `.dockerignore`; local Compose builds the same image |
| Domain | Apex, `www` and `docs.megabonkmod.party` route to port `8080` with HTTPS; `www` redirects to the apex, and the docs hostname's root redirects to `/home/` |
| Health check | `bun smoke.mjs` inside the container, the same check the Compose healthcheck runs |
| Auto-deploy | a push to `main` that touches `site/**` or `docs/**`, delivered by the Dokploy GitHub app |

Because Dokploy builds from the pushed commit, content reaches the site only after it is committed and pushed. Use `ic --env prod trigger` to re-run a deploy without a new commit, and `ic --env prod apply` only when `dokploy.yml` changes. `.dokploy-state/prod.json` maps the config's names to Dokploy's resource ids and is gitignored: `ic --env prod import` regenerates it from an existing project, and it must be present before `apply`, which otherwise creates a duplicate project. Verify a deploy from anywhere with the container's own smoke check:

```sh
curl -sI https://megabonkmod.party/          # 200, text/html
node smoke.mjs https://megabonkmod.party/    # exit 0 when every referenced asset serves
```

DNS is managed by DNSControl in the infrastructure repo's `dns/records/dnsconfig.js`, not here. The apex, `www` and `docs` are A records under `CF_PROXY_DEFAULT_OFF`, resolving directly to the host so the Let's Encrypt HTTP-01 challenge can complete. `www.megabonkmod.party` has its own router and certificate plus a Traefik `redirectRegex` to the apex at HTTP 308 with the path preserved. DNSControl changes follow the usual preview-then-push loop: `dnscontrol preview --domains megabonkmod.party` reports `0 corrections` when the zone matches the config.

Wiki canonical URLs use `https://docs.megabonkmod.party` from `site/astro.config.mjs`; the showcase retains explicit apex metadata. Build and publish the static output; no game installation or harness endpoint is needed in production beyond the static server in the image.

## Gallery API (PocketBase)

`pocketbase/` holds the backend for the community level gallery: a PocketBase 0.40 instance configured entirely from code, so a fresh data directory comes up with every collection, rule and hook in place. Nothing is built from Go; the stock release binary loads the JavaScript in `pb_migrations/` and `pb_hooks/`.

| Path | Purpose |
| --- | --- |
| `pocketbase/pb_migrations/` | Creates the `levels`, `likes` and `reports` collections and configures `users` |
| `pocketbase/pb_hooks/level_lib.js` | Level file validation, metadata derivation, share codes and filename slugs |
| `pocketbase/pb_hooks/levels.pb.js` | Upload validation, the download route and the download filename |
| `pocketbase/pb_hooks/likes.pb.js` | Recomputes `levels.likes` from the like records |
| `pocketbase/pb_hooks/oauth.pb.js` | Copies OAuth credentials from the environment on every start |
| `pocketbase/entrypoint.sh` | Starts the server; maps the environment variables below to flags |
| `pocketbase/Dockerfile` | Alpine image with a checksum-verified PocketBase release |

### API contract

- **`levels`**: `title`, `description` (at most 2000 characters), `code`, `author`, `level` (one `.json` file, at most 1 MiB), `cover` (png or jpg, at most 8 MiB, required), `biome` (optional, same limits), `packs`, `schemaVersion`, `gameBuildId`, `map`, `tags` (`Speedrun`, `Platforming`, `Survival`, `Puzzle`, `Showcase`, `Short`), `downloads`, `likes`, `hidden`, plus `created` and `updated`.
- **`likes`**: `user`, `level`; one like per pair. A client sends its own id as `user`.
- **`reports`**: `user`, `level`, `reason` (at most 1000 characters). Only an admin can read them.
- **`users`**: OAuth2 only, with GitHub, Google and Discord. Password sign-in and plain registration are off, so an account exists only after an OAuth sign-in. The user list and view rules are public so a level can expand its author; email addresses stay hidden unless a user opts in.
- **`GET /api/l/{code}/download`**: increments `downloads`, then answers `302` to `/api/files/levels/<id>/<file>?download=1`. That file URL carries `Content-Disposition: attachment; filename="<slug-of-title>.mblevel.json"`. An unknown or hidden code answers `404`. The code is matched case-insensitively.

Anyone can list and view levels where `hidden` is false. A signed-in user can create a level; only its author can update or delete it. A client can never send `code`, `downloads`, `likes`, `hidden` or `author`: the request is refused. `title`, `packs`, `schemaVersion`, `gameBuildId` and `map` are always taken from the uploaded file, whatever the client sends, so the gallery cannot disagree with what the game shows. The `code` is `XXX-XXX-XXX` in the Crockford base32 alphabet, generated on create and never changed.

A level file is accepted when it is a JSON object, `schemaVersion` is an integer from 1 to 4, `title` is non-empty (a level without one is not listed on Map Selection) and at most 200 characters, `packs` maps pack ids to version strings, and `baseline` is absent, `generated` or `none`. `edits` must be a list of objects with a non-empty `opType` and string `target` and `payload`. A from-scratch level (`baseline: none`) needs a `grid` with `width` and `depth` of at least 1 and unique cells inside it, plus a `spawn` and `bossSpawner` with a three-number `position`, and cannot carry tile edits or `gen:` targets; a generated-baseline level cannot carry a `grid`. Failures return `400` with the reasons in `data.level.message`. The checks mirror `LevelFileValidator`; see [level-format.md](level-format.md).

Pack bundles are never stored or offered. `packs` is metadata only. A hidden level's file stays reachable by its exact file URL, which contains a random suffix; the flag removes the level from listings and from the download route.

### Environment variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `PB_OAUTH_GITHUB_CLIENT_ID`, `PB_OAUTH_GITHUB_CLIENT_SECRET` | unset | GitHub OAuth app credentials |
| `PB_OAUTH_GOOGLE_CLIENT_ID`, `PB_OAUTH_GOOGLE_CLIENT_SECRET` | unset | Google OAuth client credentials |
| `PB_OAUTH_DISCORD_CLIENT_ID`, `PB_OAUTH_DISCORD_CLIENT_SECRET` | unset | Discord OAuth application credentials |
| `PB_ORIGINS` | the site origin plus `localhost` and `127.0.0.1` on ports 8080 and 4321 | Comma-separated CORS origins |
| `PB_HTTP` | `0.0.0.0:8090` | Listen address |
| `PB_DATA_DIR` | `/pb_data` | Database, uploads and backups; the image's one declared volume |
| `PB_HOOKS_DIR`, `PB_MIGRATIONS_DIR` | `/pb/pb_hooks`, `/pb/pb_migrations` | Code locations |
| `PB_BIN` | `/usr/local/bin/pocketbase` | Binary to run |

A provider is enabled only when both its id and secret are set; PocketBase rejects an empty credential. The migration applies them on first start and `oauth.pb.js` re-applies them on every start, so a secret that is set or rotated later takes effect on the next restart. Each OAuth app's redirect URL is `<api origin>/api/oauth2-redirect`. Credentials belong in the environment or an untracked `.env`, never in the repository.

### Running locally

```sh
task pocketbase:install                                # once; installs the pinned binary through mise, not .tool-versions
task pocketbase:superuser -- admin@example.test 'a-long-password'
task pocketbase:run                                    # http://127.0.0.1:8090, dashboard at /_/
task pocketbase:image                                  # builds the container image
```

Data lives in the gitignored `pocketbase/pb_data/`. `task pocketbase:test` runs `tests/test_pocketbase_service.py` and fails when the binary is missing. The same tests run under `task test` and `uv run pytest`, where they skip with the install hint instead. Set `POCKETBASE_BIN` to use a binary from elsewhere. The tests start the real `entrypoint.sh` against a temporary data directory and the real files in `levels/`, sign in as test users through superuser impersonation (password sign-in is off), and cover the validation rejections, derived fields, access rules, like counts, the download route, reports, OAuth configuration and CORS.

The image build context is `pocketbase/`: `docker build -t megabonk-levels-api pocketbase`. It builds on a pinned Alpine release and runs `apk upgrade`, downloads the PocketBase zip for the build architecture and verifies its SHA-256, runs as a non-root user and exposes port 8090 with a health check on `/api/health`. The build fails if any `openssh` package is present: the image never runs `sshd`, and the Alpine OpenSSH password-bypass advisory of 2026-11-05 is fixed in 3.24.4 and later, so keep the base tag at or above that. When bumping PocketBase, update `PB_VERSION` and both checksums from the release's `checksums.txt`, and `POCKETBASE_VERSION` in `taskfiles/pocketbase.yml` and the test file.

### Moderation

Open the dashboard at `/_/` and sign in as an admin. To remove a level from the gallery without deleting it, open `levels`, edit the record and set `hidden`; it disappears from listings and the download route at once and its author keeps their record. Review reports under `reports`, which only an admin can read; each names the reporting user, the level and a reason. Deleting a level or a user also deletes their likes and reports.

### Backups

All state is under `PB_DATA_DIR`: `data.db`, `auxiliary.db` and `storage/` (uploads). Create a backup from the dashboard under Settings, Backups, or with a `POST /api/backups` as an admin, and download the zip. To restore, stop the server, empty the data directory, unzip the backup into it and start the server again. Scheduled backups and off-box copies are configured with the deployment.

## Level gallery pages

`/levels/` (browse), `/l/<code>` (level) and `/levels/upload/` (share) are static pages that fetch from the PocketBase API in the browser with the `pocketbase` SDK. They are the one part of the site that needs JavaScript, so each page carries a `<noscript>` message that links to the manual sharing steps in the player guide.

- `site/server.mjs` serves `/l/<code>` from `levels/view/index.html`, so the level page reads the share code from `location.pathname` and shows a not-found state when it is missing or malformed. The dev server has no such rewrite: open `/levels/view/` there and the page shows not-found.
- `PUBLIC_PB_URL` is read at build time, with `http://127.0.0.1:8090` as the default, so a production build has to set it. `PUBLIC_GISCUS_REPO`, `PUBLIC_GISCUS_REPO_ID`, `PUBLIC_GISCUS_CATEGORY` and `PUBLIC_GISCUS_CATEGORY_ID` configure the giscus comment thread, which is keyed by the share code with `data-mapping="specific"`; while any is empty the level page shows a short note instead of the embed. All five are listed in `site/.env.example`.
- Sign-in uses `authWithOAuth2` for GitHub, Google and Discord, and the SDK keeps the session in `localStorage`. Likes, reports and uploads go through the collection rules, so the pages hold no secrets.
- The level file keeps its name through `/api/l/<code>/download`, which counts the download. Pack bundles are never offered; the level page lists the required packs and links to the player guide's asset pack steps.
- Search text reaches the API only through `buildFilter` in `site/src/scripts/levels.js`, which quotes it as one literal, and the tag filter accepts only the fixed tag set.

To try the pages against a local API, build the image with `task pocketbase:image`, run it on `127.0.0.1:8090`, create a superuser with `pocketbase superuser upsert`, then serve a build of the site (`node server.mjs` in `site/`, on a port in the API's allowed origins, such as 8080). Password sign-in is off, so a local test session comes from a superuser `POST /api/collections/users/impersonate/<id>` token stored in `localStorage` under `pocketbase_auth`.

## Wiki development

The wiki follows the Starlight layout used by the reference docs site: a searchable sidebar, page contents, code-block copy controls and a page-level Markdown menu. It lives inside `site/`, alongside the showcase, rather than in a separate application.

`docs/` remains authoritative. `site/scripts/sync-docs.mjs` publishes only `player-guide`, `player-installer`, `starter-level`, `music`, the three `thps-warehouse` guides and `thunderstore`. It reads each leading H1 into frontmatter and writes generated, gitignored copies under `site/src/content/docs/`. Links between published guides become `/<slug>/`; unpublished technical docs and other repository files link to GitHub with anchors preserved. Code samples are not rewritten. Unchanged pages retain their timestamps; orphan removal only touches marked generated pages. The wiki home is hand-authored in `site/src/content/docs/home.md`.

Run `npm run dev` from `site/` to sync once and watch authoritative docs with hot reload. `npm run check` also syncs before checking types. **Pagefind search requires `npm run build` and `npm run preview` or the production server**; the dev server does not build an index. The build explicitly sets production mode even if the invoking shell has `NODE_ENV=development`.

The hand-authored index uses `slug: home`, serving at `/home/` with raw Markdown at `/home.md`. Guides are served at `/<slug>/` with raw Markdown at `/<slug>.md`, so the docs hostname does not repeat `docs` in the path. The production server redirects the old `/docs/` homepage to `/home/`, `/docs/index.md` to `/home.md` and any other `/docs/<rest>` to `/<rest>`, preserving queries. Copy page fetches the same endpoint as View as Markdown, checks the response status and falls back to a temporary textarea when clipboard access is unavailable or denied. The Markdown link works without JavaScript. The three `/llms*.txt` endpoints bundle only published wiki content.

`npm test` covers sync/link rewriting and clipboard paths. `npm run test:site` checks built pages, production search markup and index files, canonical metadata, Markdown endpoints, local links, hostname redirects and the server smoke test. Use `node smoke.mjs https://docs.megabonkmod.party/` after deployment as well as the apex check; it verifies wiki routes, raw Markdown and the Pagefind JavaScript asset.

## Documentation references

Use these exact Context7 library IDs for current framework and component documentation:

- `/withastro/astro`
- `/websites/alpinejs_dev`
- `/hunvreus/basecoat`
