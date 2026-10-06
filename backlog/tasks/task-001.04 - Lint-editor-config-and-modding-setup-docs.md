---
id: TASK-001.04
title: 'Lint, editor config, and modding setup docs'
status: To Do
assignee: []
created_date: '2026-10-06 21:39'
updated_date: '2026-10-06 21:39'
labels:
  - level-editor
  - tooling
dependencies:
  - TASK-001.01
  - TASK-001.02
  - TASK-001.03
parent_task_id: TASK-001
priority: medium
type: docs
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-001 first for full context.

Add the remaining repo hygiene config, modeled on `~/git/xeno_mods` (read its `.editorconfig`, `.markdownlint.jsonc`, `.markdownlintignore`, `ruff.toml`, `.gitignore`, `.serena/project.yml` directly):

- `.editorconfig`: LF line endings, final newline, 2-space indent for json/yml, 4-space for Python/C#, matching xeno_mods.
- `.markdownlint.jsonc`: same baseline as xeno_mods (`default: true`, `MD009`/`MD013`/`MD024`/`MD031`/`MD036` off, `MD029` set to `ordered`, `MD040`/`MD060` on), plus a `.markdownlintignore` excluding `.claude/**` and `backlog/**`.
- `ruff.toml`: line-length ~130 (xeno_mods's choice), targeting the `tools/*.py` PEP 723 scripts from TASK-001.02.
- `.gitignore` additions beyond what's already in place: `bin/`, `obj/`, `Directory.Build.local.props`, `.env`, `.task/` (the go-task checksum cache), plus anything else C#/dotnet build output related. Preserve existing entries (`*.zip`, `.tools/`, `CLAUDE.md`).
- Update `.serena/project.yml` to add a C# language server entry (currently `language_servers: []`), since this repo will now contain C# source.
- `docs/modding-setup.md`: a player/contributor-facing guide — how to install MelonLoader (point to `task game:melonloader:install`), how to point a local build at your own Megabonk install (via `.env` or `Directory.Build.local.props`), and how to run/verify the mod loaded (via `task game:run` + `task game:log`). Cross-reference `.env.example` (from TASK-001.02's game_paths.py work — coordinate or just document the env vars that script exposes).

This task runs last among the TASK-001 subtasks since it documents/lints what the other three produce — sequence it after .01/.02/.03 land, or at minimum re-check its accuracy once they do.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 \.editorconfig, .markdownlint.jsonc, .markdownlintignore, and ruff.toml exist matching the xeno_mods baseline (or a deliberate, documented deviation)
- [ ] #2 .gitignore covers C#/dotnet build output, Directory.Build.local.props, .env, and .task/ without removing existing entries
- [ ] #3 .serena/project.yml has a C# language server configured
- [ ] #4 docs/modding-setup.md accurately documents MelonLoader install, local build config via .env/Directory.Build.local.props, and verifying the mod loaded via task game:run + task game:log
- [ ] #5 task lint passes cleanly against the full scaffolded repo from TASK-001.01-.03
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
