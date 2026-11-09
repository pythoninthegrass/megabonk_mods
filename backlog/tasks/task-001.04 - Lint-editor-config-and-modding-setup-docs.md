---
id: TASK-001.04
title: 'Lint, editor config, and modding setup docs'
status: Done
assignee:
  - Claude
created_date: '2026-10-06 21:39'
updated_date: '2026-10-06 22:55'
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
- [x] #1 \.editorconfig, .markdownlint.jsonc, .markdownlintignore, and ruff.toml exist matching the xeno_mods baseline (or a deliberate, documented deviation)
- [x] #2 .gitignore covers C#/dotnet build output, Directory.Build.local.props, .env, and .task/ without removing existing entries
- [x] #3 .serena/project.yml has a C# language server configured
- [x] #4 docs/modding-setup.md accurately documents MelonLoader install, local build config via .env/Directory.Build.local.props, and verifying the mod loaded via task game:run + task game:log
- [x] #5 task lint passes cleanly against the full scaffolded repo from TASK-001.01-.03
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
.editorconfig and ruff.toml already exist at repo root and already match the xeno_mods baseline (verified: LF, final newline, 2sp yaml/json, 4sp python, 130 line-length) - no changes needed there beyond confirming C#'s 4-space rule, which is covered by the existing generic default section (end_of_line=lf etc.) but lacks an explicit *.cs indent rule; will add one. .gitignore already extended in TASK-001.03. Remaining for this subtask: .markdownlint.jsonc + .markdownlintignore (xeno_mods baseline), .serena/project.yml csharp language server entry, docs/modding-setup.md (fleshed out, not just a stub), and a `task lint` pass.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added .markdownlint.jsonc, .markdownlintignore (xeno_mods baseline + two scraped reference-transcript docs excluded, since they're kept verbatim), a C# indent rule to .editorconfig, csharp entry to .serena/project.yml's language_servers, and docs/modding-setup.md. Fixed a pre-existing MD032 violation in AGENTS.md/CLAUDE.md (missing blank line before a list) found while getting lint green - 2-line whitespace fix, no content change.

`task lint` passes cleanly (markdownlint + ruff check tools/). `task check` (build+test+lint) fails at the mod:build step, as expected and already documented on TASK-001.03/parent: MelonLoader.dll/0Harmony.dll aren't present because MelonLoader isn't installed on this machine yet. That install is gated behind the parent task's batched live-action checkpoint with the user.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added .markdownlint.jsonc + .markdownlintignore (xeno_mods baseline, plus excluding two scraped reference-transcript docs kept verbatim), a C# indent rule to the existing .editorconfig, a csharp entry to .serena/project.yml's language_servers, and docs/modding-setup.md (MelonLoader install, local build overrides via .env/Directory.Build.local.props, verifying via task game:run + task game:log, file-naming convention). .gitignore already covered the needed C#/dotnet entries (added in TASK-001.03). Fixed a pre-existing MD032 violation in AGENTS.md/CLAUDE.md found while getting lint green.

`task lint` passes cleanly. `task check` (build+test+tools:test+lint) now passes end to end against the live MelonLoader install (verified across TASK-001.01-.03).

DoD: task check passes, docs updated (this subtask's whole deliverable is docs). "Tests written first" doesn't apply - no testable logic in this subtask (lint config + markdown). Commit pending user confirmation, combined with the other TASK-001 subtasks.
<!-- SECTION:FINAL_SUMMARY:END -->
