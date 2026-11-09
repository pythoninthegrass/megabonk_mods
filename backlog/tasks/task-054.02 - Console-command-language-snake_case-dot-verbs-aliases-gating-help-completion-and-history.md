---
id: TASK-054.02
title: >-
  Console command language: snake_case dot verbs, aliases, gating, help,
  completion and history
status: Done
assignee: []
created_date: '2026-11-08T07:54:00Z'
updated_date: '2026-11-08T20:41:00Z'
labels: []
dependencies: []
references:
  - scripts/run.py
  - src/MegabonkLevels.Mod/harness_command.cs
  - src/MegabonkLevels.Mod/text_field_model.cs
  - src/MegabonkLevels.Mod/env_flag.cs
  - tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj
  - tests/MegabonkLevels.Tests/harness_command_tests.cs
parent_task_id: TASK-054
priority: medium
type: feature
ordinal: 193000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The in-game console (TASK-054) needs a command language that turns a typed line into a harness command. It also needs the non-visual console behaviour: history, Tab completion, scrollback and help. All of this is pure logic and must be Unity-free, so it can be unit-tested in `tests/MegabonkLevels.Tests`. That project links individual mod source files and has no Unity references.

Binding decisions:
- **Verb style:** snake_case with dot notation for namespaces. Verb matching is case-insensitive. `"quoted strings"` are supported for arguments with spaces, such as level titles.
- **Routing:** each verb binds its arguments to the same JSON object `run.py` sends, then goes through the existing `HarnessCommand.TryParse`. Argument validation and error messages therefore match the harness. Do not duplicate handler logic.
- **Gating:** each verb carries a cheat/debug flag. When `MEGABONK_DEV` is not true, flagged verbs reply `requires MEGABONK_DEV` and never reach the dispatcher.
- **Feedback:** bad arity or bad values reply with the verb's usage line.
- **Completion:** `help [filter]` lists verbs with one-line help and aliases. Tab completes verb names and aliases by prefix and cycles through multiple matches.
- **History and scrollback:** Up/Down history lasts the session only and does not record consecutive duplicates. Scrollback is a bounded buffer of output lines and supports page scrolling.

Required verb table. A star (★) marks a gated verb. The harness command each verb maps to is in parentheses.
- Console-only: `help [filter]`, `clear` (alias `cls`), `history`.
- `state` (state).
- Player:
  - `player.teleport x y z` / `player.teleport_cell cx cy` ★, alias `tp` (teleport).
  - `player.god [on|off]` ★, alias `tgm`; no argument toggles (invulnerable/vulnerable).
  - `player.kill` ★ (kill), `player.damage n [nonlethal]` ★ (damage).
  - `player.add_item name [n]` ★ (item), `player.fall_damage` ★ (fall-damage).
- Enemies:
  - `enemies.kill nearest|all|bosses` ★, alias `killall` = all (kill-enemies).
  - `enemies.spawns on|off` ★ (spawns).
- Run:
  - `run.freeze` / `run.resume` / `run.restart` ★ (freeze/resume/restart-run).
  - `run.dismiss_levelup [n]`, `run.dismiss_offers [n|skip]`, `run.interact [type]` ★.
  - `run.press_death_confirm`, `run.press_summary_restart` ★.
- Level:
  - `level.list` (list-levels).
  - `level.load path_or_title [map/stage/tier/seed options]` ★, alias `coc`, which resolves a title against the level list (load-level).
  - `level.save [name]` ★ (save-level), `level.new [name ...]` ★ (new-level).
- Editor and camera:
  - `editor [on|off]` ★, alias `tfc`; no argument toggles (editor).
  - `camera.set x y z rx ry rz` ★ (camera), `camera.clear` ★ (camera-clear).
- UI:
  - `ui.hud [on|off]`, alias `tm` toggles (hud).
  - `ui.coordinates [on|off]` (coordinates).
- Perf:
  - `perf.<action> [...]` ★, mirroring run.py's perf actions (perf).
  - Alias `time_scale v` = perf timescale.
- Debug ★:
  - `debug.screenshot path`, `debug.query_objects type [fields]`, `debug.material_dump [object]`, `debug.shader_report`.
  - `debug.heartbeat on|off`, `debug.cells on|off`, `debug.ui_tree [x y]`, `debug.click_widget name`.
- App: `app.quit`, alias `qqq` (quit).

The music verbs are added by TASK-054.04. Its registry entries plug into the same table.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A tokenizer splits a line into verb and arguments, honouring double-quoted arguments, and is covered by tests including empty input, unterminated quotes and extra whitespace
- [x] #2 Every verb and alias in the description's table binds to the expected HarnessCommand kind and arguments via HarnessCommand.TryParse, with one test per verb
- [x] #3 Unknown verbs reply with a suggestion of the closest matching verbs; bad arity or values reply with the verb's usage line
- [x] #4 With MEGABONK_DEV not true, every starred verb replies 'requires MEGABONK_DEV' without producing a command, and unstarred verbs still bind; tested both ways
- [x] #5 Toggle verbs (player.god/tgm, editor/tfc, ui.hud/tm) with no argument flip the current state
- [x] #6 help with and without a filter lists verbs, aliases and one-line help; Tab completion cycles prefix matches; history skips consecutive duplicates; scrollback is bounded and pages; each covered by tests
- [x] #7 New files are Unity-free and linked into tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Parent closeout audit confirmed the conventional implementation commit 1d6cd44 (feat(console): add the console command language, history, completion and scrollback); reconciled the stale commit checkbox.
<!-- SECTION:NOTES:END -->
