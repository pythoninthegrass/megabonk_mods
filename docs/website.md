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

Open the URL Astro prints, normally `http://127.0.0.1:4321/`. The npm scripts bind to loopback by default. If Astro reports a detached development server, stop it from `site/` with: `npm run dev` (and `task site:dev`) also starts a local gallery API, so the gallery pages work without further setup: it runs PocketBase on `127.0.0.1:8090` with its data in the gitignored `pocketbase/pb_data_dev`, creates a dev superuser, and seeds four makers (a named one with 14 levels, one hidden; one with no display name and 3 levels; one with no levels; a site owner with 2 levels) from `site/scripts/dev-seed.mjs`. Seeding is idempotent, and a server already listening on 8090 is reused unseeded. Each start prints one line per maker with a sign-in path and the maker's `/u/<account id>` address; opening `/__dev/signin/<alice|bob|carol|owner>` on the dev server stores that maker's session in the browser and redirects to their creator page (the route exists only in the dev server, in the Vite plugin in `astro.config.mjs`). In the dev server the provider buttons the API has enabled are shown disabled (providers it has not enabled are hidden). A red bookmark at the bottom right edge slides out a strip with a user-silhouette menu that opens upward: the accounts are listed in lowercase with `Owner` first, `anonymous` last signs out, and any account signs in as that user through superuser impersonation (the dev superuser credentials are in `site/scripts/dev-seed.mjs`; the superuser never becomes the page session). A fourth seeded maker, `Owner`, is on the dev API's `PB_ADMIN_EMAILS`, so signing in as them shows the moderation controls (see Moderation); two of Alice's levels carry seeded visibility lists naming the nameless maker. A fresh browser starts signed in as `Owner` (choosing `anonymous` stops that until another user is picked), and a click anywhere outside the panel, or Escape, slides it back into the edge. The panel and its code are left out of production builds (`import.meta.env.DEV`). A shell with `NODE_ENV=development` makes `astro build` keep them, so build with `NODE_ENV=production`. PocketBase stops when the dev server exits. It needs the pinned PocketBase binary (`task pocketbase:install`, or `POCKETBASE_BIN`); without it the pages show their unreachable state. Astro backgrounds itself when it detects an agent environment, which leaves the API without an owner: run it from a normal terminal.

```sh
npm exec astro dev stop
```

## Container serving

Docker Engine with Docker Compose v2 is the only prerequisite: the image builds the site from source inside the container, so the host needs no Node, npm or game tooling. The container tooling lives with the site: `site/Dockerfile`, `site/docker-compose.yml`, `site/server.mjs` and `site/smoke.mjs`, plus the repository-root `.dockerignore`. The multi-stage Dockerfile runs `bun install --frozen-lockfile` (Bun reads `package-lock.json`, so no second lockfile exists) and `astro build` on the `oven/bun` Alpine image, then serves `dist/` with Bun from a non-root stage containing only the output, server and smoke check. The repository-root context allows the wiki sync to read `docs/`; the root `.dockerignore` (Docker reads a plain `.dockerignore` only from the context root, so it cannot live under `site/`) permits only docs and site sources and excludes dependencies, generated output, `.impeccable/`, `.env*` and logs. Game and mod assets never enter the context.

From the repository root:

```sh
docker compose up -d --build   # build and start
docker compose ps              # status, including health
docker compose logs site       # server logs
docker compose down            # stop
```

Open `http://127.0.0.1:8080/`. The published host port defaults to `8080` and is configurable through `SITE_PORT`, either per command (`SITE_PORT=8123 docker compose up -d`) or in the repository's gitignored root `.env`. The commands above run from the repository root: `COMPOSE_FILE=site/docker-compose.yml` in that `.env` (the template sets it) points Compose at the site's file, and Compose then also reads the root `.env` for `SITE_PORT`, `PUBLIC_PB_URL` and the PocketBase OAuth credentials (a `-f site/docker-compose.yml` flag would read `site/.env` instead, and running from `site/` finds no root `.env`). Build contexts still resolve from `site/`. That one file also holds the giscus values below; `.env.example` is the template, and `ic` never pushes the `SITE_`, `PUBLIC_` and `COMPOSE_` keys. Astro reads the `PUBLIC_` values from the same file (`vite.envDir` in `site/astro.config.mjs` points at the repository root), so `npm run dev` and `npm run build` need no `site/.env`. Rebuild after editing content, the server or the image itself with `up -d --build`. The service publishes on `127.0.0.1` only, serves the static files with content types and cache headers (immutable for hashed `_astro/` assets, an `ETag` on every file, and `no-cache` revalidation for HTML pages so a deploy shows at once and an unchanged page answers `304`; `SITE_HTML_CACHE_CONTROL` replaces the HTML header, for example `public, max-age=60`), and runs `bun smoke.mjs` as its health check; `ps` reports `healthy` once it passes. To run that smoke check by hand, which fetches the home page and every local CSS, JavaScript and image it references and asserts status and content type:

```sh
docker compose exec site bun smoke.mjs
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

`npm run build` produces `site/dist/`: the showcase at `/`, wiki home at `/home/` and guides at `/<slug>/`. **Content deploys on push:** Dokploy is connected to the repository through a GitHub app, and a push to `main` that touches `site/**` or `docs/**` makes it rebuild `site/Dockerfile` from the pushed commit and redeploy. Editing a guide or the site needs a commit and a push, and nothing else. The wiki pages are regenerated from `docs/` during that build, so a change to an allowlisted guide reaches the site without touching `site/`. The rest of this section covers how the Dokploy project itself is created and changed. That setup is declarative: `dokploy.yml` at the repository root describes the project, the `site` and `pocketbase` apps and their domains, and the [icarus](https://github.com/pythoninthegrass/icarus) CLI (`ic`) reconciles that file against a self-hosted Dokploy control plane through its API. The control plane's address, API key and SSH target live outside the repository in the gitignored repository-root `.env`, with the template in [`.env.example`](../.env.example) (`DOKPLOY_URL`, `DOKPLOY_API_KEY`, `DOKPLOY_ENV`, `DOKPLOY_SSH_*`). The root `.dockerignore` keeps that file out of the build context, and the credentials configure the CLI only — `dokploy.yml` sets `create_env_file: false`. Icarus reads `.env` from the working directory, so run every `ic` command from the repository root:

```sh
ic --env prod check         # credentials, reachability and config validity
ic --env prod plan          # diff against the server without writing
ic --env prod apply         # check, setup, push env, deploy in wave order
ic --env prod status        # build and deploy status per app
ic --env prod logs site     # container logs, over SSH
```

Install the CLI once from a checkout of icarus (`uv tool install <icarus checkout>`). What the config provisions:

`dokploy.yml` sets `env_targets: [pocketbase]`, so `ic env` and `ic apply` push the root `.env` to the `pocketbase` app and to no other app. Icarus pushes every key that its exclusion list does not match. The list is the built-in prefixes (including `DOKPLOY_`) plus the comma-separated `ENV_EXCLUDES` key in the same `.env`, where a trailing `_` or `*` makes a prefix match and anything else an exact match. Keep `ENV_EXCLUDES` covering every unrelated secret in the file (see `.env.example`), and check what would be pushed before an apply: with it set as in the template the only pushed keys are the `PB_OAUTH_*` values. The `site` app has no `env_targets` entry and `create_env_file: false`, so nothing from `.env` reaches it.

Some Icarus versions have incomplete reconciliation for existing apps: `plan` and `apply` do not compare or save `dockerContextPath` or GitHub `watchPaths`. When changing those fields, explicitly reconcile them through `application.saveBuildType` and `application.saveGithubProvider` before triggering the deploy. Preserve the existing GitHub provider and verify the remote owner, repository and branch first. An import can also encounter a `project.all` application summary without `appName`; obtain it from `application.one` using the summary's `applicationId`, rather than creating a replacement project.

| Piece | Value |
| --- | --- |
| Project | `megabonkmod-party`, containing the `site` and `pocketbase` apps; `pocketbase` deploys first |
| Source | GitHub `main`; Dokploy builds `site/Dockerfile` with the repository-root context, restricted by the root `.dockerignore`; local Compose builds the same image |
| Domain | Apex, `www` and `docs.megabonkmod.party` route to port `8080` with HTTPS; `www` redirects to the apex, and the docs hostname's root redirects to `/home/` |
| Health check | `bun smoke.mjs` inside the container, the same check the Compose healthcheck runs |
| Auto-deploy | a push to `main` that touches `site/**` or `docs/**`, delivered by the Dokploy GitHub app |
| API app | `pocketbase`: builds `pocketbase/Dockerfile` with `pocketbase/` as the context (the root `.dockerignore` excludes everything but `docs/` and `site/`), serves `api.megabonkmod.party` on port `8090` with HTTPS, redeploys on pushes touching `pocketbase/**`, and mounts the `pocketbase-data` volume at `/pb_data` |

Because Dokploy builds from the pushed commit, content reaches the site only after it is committed and pushed. Use `ic --env prod trigger` to re-run a deploy without a new commit, and `ic --env prod apply` only when `dokploy.yml` changes. `.dokploy-state/prod.json` maps the config's names to Dokploy's resource ids and is gitignored: `ic --env prod import` regenerates it from an existing project, and it must be present before `apply`, which otherwise creates a duplicate project. Verify a deploy from anywhere with the container's own smoke check:

```sh
curl -sI https://megabonkmod.party/          # 200, text/html
node smoke.mjs https://megabonkmod.party/    # exit 0 when every referenced asset serves
```

DNS is managed by DNSControl in the infrastructure repo's `dns/records/dnsconfig.js`, not here. The apex, `www`, `docs` and `api` are A records under `CF_PROXY_DEFAULT_OFF`, resolving directly to the host so the Let's Encrypt HTTP-01 challenge can complete. `www.megabonkmod.party` has its own router and certificate plus a Traefik `redirectRegex` to the apex at HTTP 308 with the path preserved. DNSControl changes follow the usual preview-then-push loop: `dnscontrol preview --domains megabonkmod.party` reports `0 corrections` when the zone matches the config.

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
| `pocketbase/pb_hooks/ratelimit.pb.js`, `ratelimit_lib.js` | Applies the rate limits and the trusted proxy header from the environment on every start |
| `pocketbase/entrypoint.sh` | Starts the server; maps the environment variables below to flags |
| `pocketbase/Dockerfile` | Alpine image with a checksum-verified PocketBase release |

### API contract

- **`levels`**: `title`, `description` (at most 2000 characters), `code`, `author`, `level` (one `.json` file, at most 1 MiB), `cover` (png or jpg, at most 8 MiB, required), `biome` (optional, same limits), `packs`, `schemaVersion`, `gameBuildId`, `map`, `tags` (`Speedrun`, `Platforming`, `Survival`, `Puzzle`, `Showcase`, `Short`), `downloads`, `likes`, `hidden`, `viewers` and `blocked` (lists of users, see below), plus `created` and `updated`.
- **`likes`**: `user`, `level`; one like per pair. A client sends its own id as `user`.
- **`packs`**: one record per uploaded pack version. `packId` (lowercase letters, digits, hyphens and underscores, at most 64 characters, starting with a letter or digit, so it is a safe folder name), `version`, `name` and `assetCount` (all read from `manifest.json`), `description` (at most 2000 characters), `author`, `manifest` and `attachments` (JSON files, at most 256 KiB each), `bundleWindows` and `bundleLinux` (at least one is required), `sizeWindows` and `sizeLinux` (bytes, 0 for a platform with no bundle), `attested`, `downloads`, `hidden`, `viewers` and `blocked`, plus `created` and `updated`. `packId` and `version` are unique together.
- **`reports`**: `user`, exactly one of `level` or `pack`, `category` (`copyright`, `broken`, `inappropriate` or `other`; `other` when omitted), `reason` (at most 1000 characters, required unless the category is `copyright`), and the server-set `status` (`new`, `incomplete`, `needs-info`, `valid` or `rejected`), `missing` and `notifiedAt`. A copyright report also carries `contactEmail`, `contactAddress`, `contactPhone`, `work`, `itemUrl`, `goodFaith`, `accurate`, `fairUseConsidered` and `signature`. Only an admin can read them. See Reports and copyright below.
- **`users`**: OAuth2 only, with an `admin` flag that marks the site owners (see Moderation), with GitHub, Google and Discord. Password sign-in and plain registration are off, so an account exists only after an OAuth sign-in. The user list and view rules are public so a level can expand its author; email addresses stay hidden unless a user opts in.
- **`GET /api/l/{code}/download`**: increments `downloads`, then answers `302` to `/api/files/levels/<id>/<file>?download=1`. That file URL carries `Content-Disposition: attachment; filename="<slug-of-title>.mblevel.json"`. An unknown code, or one the caller may not see under the visibility rules below, answers `404`. The code is matched case-insensitively.
- **`GET /api/p/{id}/download?platform=windows|linux[&version=<v>]`**: increments the pack record's `downloads` and answers a zip named `<id>-<version>-<platform>.zip` that holds `<id>/<id>` (the bundle), `<id>/manifest.json` and `<id>/attachments.json`, so unzipping it into `UserData/LevelPacks/` installs the pack. The newest visible version is served unless `version` names another. A bad `platform` answers `400`; an unknown pack, a version or platform that does not exist, or a pack the caller may not see answers `404`. The hook links the stored files under those names and runs the system `zip` (the image installs it), because PocketBase's JS hooks have no zip API.

A level is visible to its author, to site owners, to anyone when `hidden` is false and they are not in `blocked`, and to anyone in `viewers` when `hidden` is true. A signed-in user can create a level; only its author or a site owner can delete it, and only its author or a site owner can update it. An author can never send `code`, `downloads`, `likes`, `hidden`, `viewers`, `blocked` or `author`: the request is refused, so only site owners change visibility. A site owner can never send `code`, `downloads`, `likes` or `author` either. `viewers` and `blocked` are removed from every response except to site owners, and a list or view request by anyone else that names them in `filter`, `sort` or `expand` (outside a quoted string) answers `400`, so the lists cannot be probed through a query. `title`, `packs`, `schemaVersion`, `gameBuildId` and `map` are always taken from the uploaded file, whatever the client sends, so the gallery cannot disagree with what the game shows. The `code` is `XXX-XXX-XXX` in the Crockford base32 alphabet, generated on create and never changed.

A level file is accepted when it is a JSON object, `schemaVersion` is an integer from 1 to 4, `title` is non-empty (a level without one is not listed on Map Selection) and at most 200 characters, `packs` maps pack ids to version strings, and `baseline` is absent, `generated` or `none`. `edits` must be a list of objects with a non-empty `opType` and string `target` and `payload`. A from-scratch level (`baseline: none`) needs a `grid` with `width` and `depth` of at least 1 and unique cells inside it, plus a `spawn` and `bossSpawner` with a three-number `position`, and cannot carry tile edits or `gen:` targets; a generated-baseline level cannot carry a `grid`. Failures return `400` with the reasons in `data.level.message`. The checks mirror `LevelFileValidator`; see [level-format.md](level-format.md).

A level's `packs` map stays metadata: the level page looks up hosted packs by id and links them, and flags a pack whose hosted versions do not include the version the level records. The mod never fetches a pack on its own; downloads are manual.

Pack uploads follow the same visibility rules as levels (`hidden`, `viewers`, `blocked`, with the lists shown only to site owners). A signed-in user can create a pack only with `attested` true; the request is refused otherwise. An author cannot send `downloads`, `hidden`, `viewers`, `blocked`, `author`, `sizeWindows` or `sizeLinux`, and only site owners can update a pack, so an author publishes a new version instead of editing one, and can delete their own. The create hook (`pack_lib.js`) reads `manifest.json`, `attachments.json` and the sizes and answers `400` with one message per field: `manifest` is checked with the `PackManifest.Parse` rules (valid JSON object, string `id` equal to `packId`, non-empty string `version`, `assets` a list of strings, `name` and `author` strings when present), `attachments` must be a JSON object, at least one bundle is required, and the upload can be at most 30 MiB across all files. The per-field `maxSize` is 256 KiB for each JSON file and 30 MiB for each bundle; the 30 MiB total is checked by the hook, since two bundle caps cannot share one limit. A `packId` belongs to its first uploader: another player's upload under that id is refused on `packId`, while a site owner can add a version and the record stays under the original author. A version already uploaded under that id is refused. The 30 MiB limit was exercised against PocketBase's own request handling in the tests; the Traefik and Dokploy proxy limits on the VPS have not been checked.

A hidden level's file stays reachable by its exact file URL, which contains a random suffix; the flag removes the level from listings and from the download route.

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
| `PB_BACKUP_CRON` | `0 3 * * *` | Scheduled backup cron expression |
| `PB_BACKUP_KEEP` | `7` | Number of scheduled backups kept |
| `PB_RATE_LIMITS_ENABLED` | `true` | `false` turns the rate limiter off |
| `PB_RATE_LIMIT_RULES` | see [Rate limiting](#rate-limiting) | Comma-separated `<label> <max requests> <seconds>` rules; replaces the whole list |
| `PB_TRUSTED_PROXY_HEADERS` | `X-Forwarded-For` | Comma-separated headers that carry the real client IP behind the reverse proxy |

A provider is enabled only when both its id and secret are set; PocketBase rejects an empty credential. The migration applies them on first start and `oauth.pb.js` re-applies them on every start, so a secret that is set or rotated later takes effect on the next restart. Each OAuth app's redirect URL is `<api origin>/api/oauth2-redirect`. Credentials belong in the environment or an untracked `.env`, never in the repository.

### Running locally

```sh
task pocketbase:install                                # once; installs the pinned binary through mise, not .tool-versions
task pocketbase:superuser -- admin@example.test 'a-long-password'
task pocketbase:run                                    # http://127.0.0.1:8090, dashboard at /_/
task pocketbase:image                                  # builds the container image
```

Data lives in the gitignored `pocketbase/pb_data/`. `task pocketbase:test` runs `tests/test_pocketbase_service.py` and fails when the binary is missing. The same tests run under `task test` and `uv run pytest`, where they skip with the install hint instead. Set `POCKETBASE_BIN` to use a binary from elsewhere. The tests start the real `entrypoint.sh` against a temporary data directory and the real files in `levels/`, sign in as test users through superuser impersonation (password sign-in is off), and cover the validation rejections, derived fields, access rules, like counts, the download route, reports, OAuth configuration and CORS. `tests/test_pocketbase_packs.py` and `tests/test_pocketbase_reports.py` reuse its fixtures and cover pack uploads, manifest validation, the 30 MiB limit, id ownership, the zip layout, report categories and the copyright report flow; the report tests run a small local SMTP server to read the notice mailed to an uploader.

The image build context is `pocketbase/`: `docker build -t megabonk-levels-api pocketbase`. It builds on a pinned Alpine release, runs `apk upgrade`, installs `zip` for the pack download route, downloads the PocketBase zip for the build architecture and verifies its SHA-256, runs as a non-root user and exposes port 8090 with a health check on `/api/health`. The build fails if any `openssh` package is present: the image never runs `sshd`, and the Alpine OpenSSH password-bypass advisory of 2026-11-05 is fixed in 3.24.4 and later, so keep the base tag at or above that. When bumping PocketBase, update `PB_VERSION` and both checksums from the release's `checksums.txt`, and `POCKETBASE_VERSION` in `taskfiles/pocketbase.yml` and the test file.

### Rate limiting

`pb_hooks/ratelimit.pb.js` enables PocketBase's rate limiter on every start, so the limits are code rather than dashboard state. A rule is `<label> <max requests per IP> <seconds>`. The label is a tag such as `levels:create` or `*:auth`, a complete path, or a path prefix ending in `/`; a label may contain spaces, such as `POST /api/collections/`. PocketBase applies the most specific matching rule whatever the order of the list, and superusers are never limited. Over the limit a client gets `429` with `Too Many Requests.`.

| Rule | Limit per IP | Covers |
| --- | --- | --- |
| `*:auth` | 2 per 3 s | Sign-in attempts |
| `*:create` | 20 per 5 s | Every create, including likes and reports |
| `/api/batch` | 3 per 1 s | The batch endpoint |
| `/api/` | 300 per 10 s | Everything else |
| `/api/l/` | 30 per 60 s | The download route, which increments the public counter |
| `levels:create` | 10 per 60 s | Level uploads, which carry large image files |

The first four are PocketBase's suggested defaults. `PB_RATE_LIMIT_RULES` replaces the whole list in the same format, and a malformed entry stops the server with the entry in the error. Behind the reverse proxy every request reaches PocketBase from the proxy's address, so the limiter would give all visitors one shared budget. `PB_TRUSTED_PROXY_HEADERS` (default `X-Forwarded-For`) names the header that carries the real client address; the hook reads the proxy-appended end of that header, so a client cannot choose its own address, provided the API is reachable only through the proxy. The service tests cover the defaults, the environment overrides, specific-over-prefix matching and separate budgets per forwarded address.

### Moderation

Site owners are the accounts whose email is listed in `PB_ADMIN_EMAILS` (comma separated, case-insensitive, in the gitignored root `.env` and pushed with `ic env`). The hook in `pocketbase/pb_hooks/admins.pb.js` sets the `users.admin` flag from that list on every start and whenever an account is created, so removing an email revokes the powers at the next restart, and nobody can set the flag through the API. An account created by an OAuth sign-in with a listed email gets the flag at once; an account that already exists gets it at the next start.

A signed-in owner sees, on every level card and on the level page, the edit pencil (for any maker's level; the upload page looks the level up by its code), an eye icon that hides or shows the level for the public and a trash icon that deletes it after a confirmation. Hidden levels stay visible to their maker and to owners, with a greyscale, faded cover and a "Hidden" tag on cards. The level page also has a Visibility panel with two per-user lists: "Can see it while hidden" (`viewers`) and "Cannot see it" (`blocked`, which removes a public level for that user; the maker is never blocked from their own level). The site only offers these controls to accounts with the flag; the API rules are what enforce them.

Open the dashboard at `/_/` and sign in as an admin. To remove a level from the gallery without deleting it, open `levels`, edit the record and set `hidden`; it disappears from listings and the download route at once and its author keeps their record. Review reports under `reports`, which only an admin can read; each names the reporting user, the level or pack, a category and a reason. Deleting a level, a pack or a user also deletes their likes and reports. The same dashboard hides a pack: open `packs`, edit the record and set `hidden`.

### Reports and copyright

Anyone signed in can report a level or a pack from its page, choosing a category. Hosting is reporting-based: the upload form has a required attestation checkbox ("I made this pack or have the right to share it") with a tooltip that says what may be shared (your own work, assets under a licence that allows redistribution) and what may not (assets ripped from games or other copyrighted material, including the THPS Warehouse pack built locally from the game files), and a report is how a rights holder removes something.

Choosing the copyright category shows the copyright form: a warning that false reports are misuse and can end in account termination or legal consequences, a note that the reporter's name, email address and the description of the work are shared with the uploader while the postal address and phone number are not, at least one way to be contacted, the description of the work, the link to the reported item (filled in from the page), a fair-use confirmation, a good-faith statement, an accuracy statement made under penalty of perjury, and a typed full-name signature. One report covers one level or pack.

The report hook (`report_lib.js`) records what a copyright report lacks in `missing` and files it as `incomplete` rather than `new`; the item link must name the reported item (`/l/<code>` or `/p/<id>`). Nothing is removed on receipt. An owner reads the report in the dashboard and sets `status`:

- `needs-info`: ask the reporter for the missing details by the contact they gave, then fix the fields in the dashboard (`missing` is recomputed on every save) or wait for a new report. The item stays up meanwhile.
- `rejected`: nothing changes.
- `valid`: refused with a message while `missing` is not empty, so an incomplete report can never remove anything. On a complete one the item's `hidden` flag is set and the uploader is mailed, with the description of the work and the reporter's name and email for a copyright report, and `notifiedAt` is set. A failed mail is logged and leaves `notifiedAt` empty. Setting `valid` again does not mail twice.

Mail needs the SMTP settings in the dashboard (Settings, Mail). Counter-notification, retraction, repeat-offender tracking and prevent-reupload are not built. Whether to register a DMCA designated agent and publish a takedown and repeat-infringer policy is an open question to settle before launch; without it the site may lose US safe-harbour protection.

### Backups

All state is under `PB_DATA_DIR`: `data.db`, `auxiliary.db` and `storage/` (uploads). `pb_hooks/backups.pb.js` sets the backup schedule from `PB_BACKUP_CRON` and `PB_BACKUP_KEEP` on every start, so the schedule is code rather than dashboard state. Backups are zip files in `<PB_DATA_DIR>/backups`, which is on the volume; there is no off-box copy yet. Create one on demand from the dashboard under Settings, Backups, or with an admin `POST /api/backups`, and download the zip.

To restore, stop the server, empty the data directory, unzip the backup into it and start the server again. To rehearse a restore without touching production, unzip a backup into an empty directory and start a second instance against it:

```sh
unzip pb_backup_<name>.zip -d /tmp/pb_restore
PB_DATA_DIR=/tmp/pb_restore PB_HTTP=127.0.0.1:8091 sh pocketbase/entrypoint.sh
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8091/api/health   # 200
```

### Production deployment

- **DNS.** Add an `api` A record to the same host as the apex, DNS-only so the Let's Encrypt HTTP-01 challenge resolves, in the DNSControl config.
- **Order.** `dokploy.yml` deploys `pocketbase` before `site`. Run `ic --env prod apply` from the repository root, never before `.dokploy-state/prod.json` is present.
- **Volume.** `pocketbase-data` is a Docker-managed volume at `/pb_data`, so levels, uploads, accounts and backups survive redeploys. Do not delete the volume when recreating the app.
- **Environment.** Put the `PB_OAUTH_*` values in the root `.env` and run `ic --env prod env`, then redeploy the app. They reach Dokploy through `env_targets`, never through the repository.
- **OAuth apps.** Register one OAuth app per provider (GitHub, Google, Discord) with the redirect URL `https://api.megabonkmod.party/api/oauth2-redirect`. A provider whose id and secret are unset is simply not offered on the sign-in buttons.
- **First admin.** Create the superuser inside the running container with `pocketbase superuser upsert <email> <password> --dir=/pb_data`, using `ic exec`.
- **Check.** `curl -sI https://api.megabonkmod.party/api/health` answers 200 once the certificate is issued.

### giscus setup

These are manual steps on the GitHub repository, since giscus reads Discussions through its GitHub app:

1. Enable Discussions in the repository settings.
2. Create a Discussions category named `Levels` (type Announcement, so only maintainers and giscus open threads).
3. Install the [giscus app](https://github.com/apps/giscus) on the repository.
4. Open <https://giscus.app/>, enter the repository and the `Levels` category, and copy the generated `data-repo-id` and `data-category-id`.
5. Put the four public values (`PUBLIC_GISCUS_REPO`, `PUBLIC_GISCUS_REPO_ID`, `PUBLIC_GISCUS_CATEGORY`, `PUBLIC_GISCUS_CATEGORY_ID`) into the build-argument defaults in `site/Dockerfile`, which currently point at the Announcements category.

## Level gallery pages

`/levels/` (browse), `/l/<code>` (level), `/u/<account id>` (creator), `/levels/upload/` (share a level), `/p/<pack id>` (pack) and `/packs/upload/` (share a pack) are static pages that fetch from the PocketBase API in the browser with the `pocketbase` SDK. They are the one part of the site that needs JavaScript, so each page carries a `<noscript>` message that links to the manual sharing steps in the player guide.

- `site/server.mjs` serves `/l/<code>` from `levels/view/index.html` using the patterns in `site/routes.mjs`, which the Astro dev server shares through a Vite plugin in `astro.config.mjs`, so the level page reads the share code from `location.pathname` and shows a not-found state when it is missing or malformed.
- `/u/<account id>` is the creator page, served from `creators/view/index.html` for any 15 character lowercase alphanumeric id; the page reads the id from `location.pathname`. A creator is identified by account id because display names can be empty or duplicated. The page reads three public account fields (`id`, `name`, `created`, listed as `CREATOR_FIELDS` in `site/src/scripts/gallery.js`) and never requests email. The level count and the like and download totals come from a `getFullList` of the creator's levels limited to the `likes` and `downloads` fields, so they cover every visible level rather than one page; the thumbnails come from a 12-per-page `getList` sorted newest first, with Previous and Next. The collection's list rule already excludes hidden levels. The maker's name on the browse cards and the level page links here, labelled "Unknown maker" when the display name is empty, and the owner's edit icon shows on their own thumbnails.
- `PUBLIC_PB_URL` is read at build time and baked into the pages. The container build takes it as the `PUBLIC_PB_URL` build argument, which defaults to the production API at `https://api.megabonkmod.party`; the Compose file passes `http://127.0.0.1:8090` (or your `site/.env` value) so a local image talks to a local API, and `npm run build` outside Docker falls back to the same local address. `PUBLIC_GISCUS_REPO`, `PUBLIC_GISCUS_REPO_ID`, `PUBLIC_GISCUS_CATEGORY` and `PUBLIC_GISCUS_CATEGORY_ID` configure the giscus comment thread, which is keyed by the share code with `data-mapping="specific"` and strict title matching, so a discussion's title is exactly the code; while any is empty the level page shows a short note instead of the embed. All five are listed in `site/.env.example`. The container build also takes the four giscus values as build arguments; their defaults in `site/Dockerfile` are the repository's public giscus ids (repository, repository id, the Announcements category and its id), which are not secrets.
- Sign-in uses `authWithOAuth2` for GitHub, Google and Discord, and the SDK keeps the session in `localStorage`. Likes, reports and uploads go through the collection rules, so the pages hold no secrets.
- The heart and download counts beside the maker's name on the level page are controls, as on the browse cards. The heart toggles the same like as the Like button in the "Like or report" section, shares its liked state and count, and is disabled while a request is in flight; signed out, it scrolls to the sign-in buttons in that section. The download count links to the counted download and goes up by one in the page on click.
- The level file keeps its name through `/api/l/<code>/download`, which counts the download. The level page lists the required packs; each one hosted here links to `/p/<id>`, one whose hosted versions lack the recorded version carries a "Hosted here" flag naming the hosted version, and one that is not hosted says so and keeps the link to the player guide's asset pack steps (`hostedPacks` in `site/src/scripts/packs.js`).
- `/p/<pack id>` is served from `packs/view/index.html` for any id that fits the pack id pattern in `site/routes.mjs`. It shows the id, version, maker, asset count, platforms with sizes and every version (`?v=<version>` picks one), a per-platform Download link to `/api/p/<id>/download`, install steps and the report form. `/packs/upload/` takes the manifest, attachments, bundles, description and the attestation checkbox with its tooltip, checks the 30 MiB total in the browser before sending, and lists the maker's own packs with a delete button.
- The report form (`site/src/components/ReportForm.astro` with `site/src/scripts/report-form.js`) is shared by the level and pack pages; `reportPayload` in `site/src/scripts/reports.js` sends the copyright fields only for the copyright category.
- Search text reaches the API only through `buildFilter` in `site/src/scripts/levels.js`, which quotes it as one literal, and the tag filter accepts only the fixed tag set.

To try the pages against a local API, build the image with `task pocketbase:image`, run it on `127.0.0.1:8090`, create a superuser with `pocketbase superuser upsert`, then serve a build of the site (`node server.mjs` in `site/`, on a port in the API's allowed origins, such as 8080). Password sign-in is off, so a local test session comes from a superuser `POST /api/collections/users/impersonate/<id>` token stored in `localStorage` under `pocketbase_auth`.

## Wiki development

The wiki follows the Starlight layout used by the reference docs site: a searchable sidebar, page contents, code-block copy controls and a page-level Markdown menu. It lives inside `site/`, alongside the showcase, rather than in a separate application.

`docs/` remains authoritative. `site/scripts/sync-docs.mjs` publishes only `player-guide`, `player-installer`, `starter-level`, `music`, the three `thps-warehouse` guides and `thunderstore`. It reads each leading H1 into frontmatter and writes generated, gitignored copies under `site/src/content/docs/`. Links between published guides become `/<slug>/`; unpublished technical docs and other repository files link to GitHub with anchors preserved. Code samples are not rewritten. Unchanged pages retain their timestamps; orphan removal only touches marked generated pages. The wiki home is hand-authored in `site/src/content/docs/home.md`.

From the repository root, `task site:dev` runs the dev server on `http://127.0.0.1:4321`, and `task site:serve` builds the site and serves `site/dist` with the production server on `http://127.0.0.1:8080` (`SITE_PORT` overrides the port). `task site:build`, `site:test`, `site:check` and `site:lint` run the matching npm and Deno checks, and each installs dependencies first when `package-lock.json` has changed. `site:build` skips the build while the site sources, `docs/` and the `.env` files are unchanged; pass `--force` to rebuild anyway. Run `npm run dev` from `site/` to sync once and watch authoritative docs with hot reload. `npm run check` also syncs before checking types. **Pagefind search requires `npm run build` and `npm run preview` or the production server**; the dev server does not build an index. The build explicitly sets production mode even if the invoking shell has `NODE_ENV=development`.

The hand-authored index uses `slug: home`, serving at `/home/` with raw Markdown at `/home.md`. Guides are served at `/<slug>/` with raw Markdown at `/<slug>.md`, so the docs hostname does not repeat `docs` in the path. The production server redirects the old `/docs/` homepage to `/home/`, `/docs/index.md` to `/home.md` and any other `/docs/<rest>` to `/<rest>`, preserving queries. Copy page fetches the same endpoint as View as Markdown, checks the response status and falls back to a temporary textarea when clipboard access is unavailable or denied. The Markdown link works without JavaScript. The three `/llms*.txt` endpoints bundle only published wiki content.

`npm test` covers sync/link rewriting and clipboard paths. `npm run test:site` checks built pages, production search markup and index files, canonical metadata, Markdown endpoints, local links, hostname redirects and the server smoke test. Use `node smoke.mjs https://docs.megabonkmod.party/` after deployment as well as the apex check; it verifies wiki routes, raw Markdown and the Pagefind JavaScript asset.

## Documentation references

Use these exact Context7 library IDs for current framework and component documentation:

- `/withastro/astro`
- `/websites/alpinejs_dev`
- `/hunvreus/basecoat`
