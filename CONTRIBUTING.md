# Contributing

This repository holds an unofficial [Megabonk](https://store.steampowered.com/app/3405340/Megabonk/)
mod: an in-game level editor, a console, and a development harness with MCP tools,
plus the player installer and the [showcase and wiki](https://megabonkmod.party).

Please open an issue before any change bigger than a typo so the design can be
agreed before code is written, and keep one topic per pull request.

## What lives where

| Path | Contents |
| --- | --- |
| `src/MegabonkLevels.Mod/` | the BepInEx plugin: editor, console, harness |
| `scripts/`, `tools/` | Python helpers with PEP 723 headers, run through `uv run` |
| `tests/` | Python tests, run by `pytest` |
| `go/` | the Go player installer |
| `levels/` | level JSON with its preview images |
| `docs/` | authoritative documentation |
| `site/` | Astro showcase and Starlight player wiki |
| `pkg/` | Thunderstore package contents |
| `taskfile.yml`, `taskfiles/` | `task` entry points |

## Setup

[mise](https://mise.jdx.dev) pins the toolchain in `.tool-versions` (task, uv,
Python 3.13, .NET 10, Go 1.27, Deno, ruff, bun, jq); `mise install` fetches them.

```sh
cp .env.example .env    # your local game paths; never committed
uv sync
```

The mod needs a Steam copy of the **Windows** game build with BepInEx 6 IL2CPP
installed and launched once, as covered in
[modding setup](docs/modding-setup.md). Native Linux mod support is unverified.

## Build and run

```sh
task mod:build    # build and deploy the DLL into your game install
task game:run
```

BepInEx loads the plugin at startup, so a rebuild only takes effect on a fresh
launch:

```sh
uv run scripts/run.py relaunch levels/bramblecrown-hill.mblevel.json
```

## Checks

Nothing runs on pull requests: the only workflow is release-please on push to
`main`. The commands below are the gate, so run them before opening a pull request.

| Command | Covers | Game install needed |
| --- | --- | --- |
| `task check` | build, installer, .NET and Python tests, lint | yes |
| `task mod:test` | .NET unit tests | no |
| `task scripts:test` | Python tests under `tests/` | no |
| `task installer:test` | `gofmt`, `go vet`, and Go tests | no |
| `task lint` | markdownlint, ruff over `scripts/`, `tests/` and `tools/`, and the site checks | no |
| `task site:lint` | `deno fmt --check` and `deno lint` over the site's JavaScript | no |
| `task site:dev` / `task site:serve` | Run the Astro dev server, or build and serve the production site on port 8080 | no |
| `npm run check` | Astro types and the wiki sync, run from `site/` | no |
| `npm test` | clipboard, copy, and docs-sync tests, run from `site/` | no |
| `npm run test:site` | page, server, and wiki checks, run from `site/` after `npm run build` | no |

Website-only changes need the site commands, not a mod rebuild. They need the site's
dependencies installed first, with `npm ci` in `site/`.

## Commits

Versions and release notes come from
[release-please](https://github.com/googleapis/release-please), which reads commit
subjects on `main`, so they must be
[Conventional Commits](https://www.conventionalcommits.org/):

```text
fix(wine): distinguish unchanged installs from completed repairs
feat(site): add searchable player wiki
```

`feat`, `fix`, and `perf` reach `CHANGELOG.md`; other types are release neutral.
Use `feat!:` or a `BREAKING CHANGE:` footer for a major bump, and keep the scope
attached to the type: `chore (docs): ...` with a space before the parenthesis does
not parse.

Leave no tool watermark anywhere. No `Co-Authored-By` or `Generated with` footers,
and no agent, harness, or model names in commits, code, or documents.

## Code style

`.editorconfig` governs whitespace: LF endings, a final newline, tabs in Go, four
spaces in Python and C#, two in YAML and JSON.

- Comments run at most one or two lines above a function, method, or field, and
  only when the name does not already say what it is. No section banners or
  multi-paragraph blocks: rationale belongs in `docs/`.
- Python follows `ruff.toml`: line length 130, target Python 3.13, autofix on.
  Helpers under `scripts/` and `tools/` are invoked as `uv run scripts/x.py`, so
  the executable bit and the shebang are not load-bearing.
- JavaScript and TypeScript under `site/` are checked by Deno against
  `site/deno.jsonc`: `deno lint`, and `npm run fmt` from `site/` to format. The two
  rules that assume a Deno runtime stay off, because those scripts run under Node.
- Markdown is linted by `task lint` against `.markdownlint.jsonc`. That scan only
  picks up `*.md` files, so keep the extension on new documents.

## Documentation

`docs/` is authoritative and uses kebab-case file names. The player wiki publishes
an explicit allowlist read by `site/scripts/sync-docs.mjs`: the player guide, the
legacy player installer, the starter level, music, the three THPS warehouse guides,
and the Thunderstore guide. Publishing a new guide means adding it to that
allowlist; every other document is linked to GitHub. Never edit the generated copies
under `site/src/content/docs/docs/`, apart from the hand-authored `index.md`.

Document the schema, the rule, the API, or the gotcha itself, not the work item
that introduced it: no task identifiers, acceptance-criteria numbers, or "per the
finding in" prose. A genuinely open question belongs in the document as a TODO
phrased about the question.

Capture screenshots through the
[retained screenshot workflow](docs/development.md#retaining-screenshots), keep
meaningful alt text and independent captions, and remember that game imagery stays
the property of its rights holders.

## Assets and licensing

The repository is released under the Unlicense in [LICENSE](LICENSE).

Do not commit:

- game assemblies, extracted game assets, or anything copied out of a game install;
- extracted THPS assets or music (`*.mp3`, `*.flac`), and reference captures under
  `tools/` or any `videos/` directory;
- build products such as `tools/steamstub/steam_api64.dll` and `pkg/` output that a
  task regenerates;
- your `.env`, or any token, in a commit or an issue.

Vendored third-party code keeps its upstream license beside it, the way
`pkg/NLayer.LICENSE.txt` does for the MIT-licensed NLayer, and a new dependency
means recording its license the same way. The Thunderstore package stays
runtime-only: no levels, packs, or music. Adding a level or a pack is a separate
licensing and manager-layout review, described in
[Thunderstore packaging](docs/thunderstore.md).

## Generated files

Regenerate these rather than editing them by hand:

| File or directory | Source |
| --- | --- |
| `levels/thps.mblevel.json` | `scripts/build_thps_level.py` |
| `unity/pack-authoring/Assets/Thps` | `task thps:pack --force` |
| `pkg/` bundle | `task package:thunderstore` |
| `site/src/content/docs/docs/` | `npm run sync:docs`, run from `site/` |
| `CHANGELOG.md`, `.release-please-manifest.json`, version fields | release-please |

## Optional pre-commit hooks

The hooks run the same checks as `task lint` — markdownlint, ruff, and the site's
Deno lint and format check — plus `gofmt`, `go vet`, and file hygiene for stray
whitespace, conflict markers, and malformed JSON or YAML. They are opt-in and
`task check` remains the gate. The file is `.pre-commit-config.yml`, which is not the
name pre-commit looks for by default, so every invocation needs `-c`:

```sh
pre-commit install -c .pre-commit-config.yml
pre-commit run --all-files -c .pre-commit-config.yml
```

## Code of conduct

### Our pledge

In the interest of fostering an open and welcoming environment, we as contributors
and maintainers pledge to making participation in our project and our community a
harassment-free experience for everyone, regardless of age, body size, disability,
ethnicity, gender identity and expression, level of experience, nationality,
personal appearance, race, religion, or sexual identity and orientation.

### Our standards

Examples of behavior that contributes to creating a positive environment include:

- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

Examples of unacceptable behavior by participants include:

- The use of sexualized language or imagery and unwelcome sexual attention or advances
- Trolling, insulting or derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information, such as a physical or electronic address,
  without explicit permission
- Other conduct which could reasonably be considered inappropriate in a professional
  setting

### Our responsibilities

Project maintainers are responsible for clarifying the standards of acceptable
behavior and are expected to take appropriate and fair corrective action in response
to any instances of unacceptable behavior.

Project maintainers have the right and responsibility to remove, edit, or reject
comments, commits, code, wiki edits, issues, and other contributions that are not
aligned to this Code of Conduct, or to ban temporarily or permanently any
contributor for other behaviors that they deem inappropriate, threatening,
offensive, or harmful.

### Scope

This Code of Conduct applies both within project spaces and in public spaces when an
individual is representing the project or its community. Examples of representing a
project or community include using an official project e-mail address, posting via an
official social media account, or acting as an appointed representative at an online
or offline event. Representation of a project may be further defined and clarified by
project maintainers.

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported
by opening an issue or contacting the maintainer,
[@pythoninthegrass](https://github.com/pythoninthegrass). All complaints will be
reviewed and investigated and will result in a response that is deemed necessary and
appropriate to the circumstances. The maintainer is obligated to maintain
confidentiality with regard to the reporter of an incident. Further details of
specific enforcement policies may be posted separately.

Project maintainers who do not follow or enforce the Code of Conduct in good faith
may face temporary or permanent repercussions as determined by other members of the
project's leadership.

### Attribution

This Code of Conduct is adapted from the [Contributor Covenant](https://www.contributor-covenant.org),
version 1.4, available at
[contributor-covenant.org/version/1/4](https://www.contributor-covenant.org/version/1/4/).

## License

By contributing, you agree that your contribution is released under the Unlicense in
[LICENSE](LICENSE), the same public-domain dedication as the rest of the repository.
Vendored code keeps its own license and stays under its original terms.
