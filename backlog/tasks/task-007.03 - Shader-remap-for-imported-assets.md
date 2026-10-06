---
id: TASK-007.03
title: Shader remap for imported assets
status: To Do
assignee: []
created_date: '2026-10-06 21:44'
labels:
  - level-editor
  - assets
dependencies:
  - TASK-007.02
parent_task_id: TASK-007
priority: low
type: feature
ordinal: 35000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-007 first for full context.

An AssetBundle authored in a different Unity project likely bakes in shader references (e.g. Standard/URP shaders) that don't exist or don't match Megabonk's actual shader set (the game uses MK.Toon and Post Processing v2 per earlier research — confirm exact shaders in use). At load time, remap materials coming from loaded packs onto equivalent shaders the game actually ships, using `Shader.Find` against the game's real shader names (identify these concretely — don't assume MK.Toon's shader names without checking), so imported assets render with a visually consistent, in-style appearance rather than pink/missing-shader errors or an obviously out-of-place PBR look.

Verify visually on at least one non-trivial imported model (not just a flat-colored cube) from TASK-007.01's test bundle or a new one, confirming the remapped material looks reasonably in-style, not just "not pink".
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Materials on assets loaded from a pack are remapped from their authoring-project shaders onto Megabonk's actual in-game shaders (confirmed exact shader names, e.g. MK.Toon)
- [ ] #2 A non-trivial imported model (not a flat-colored primitive) renders without missing-shader (pink) errors after remap
- [ ] #3 The remapped appearance is visually assessed as reasonably in-style, not just technically non-broken
- [ ] #4 The exact shader names/mapping rules used are documented for future asset authors
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
