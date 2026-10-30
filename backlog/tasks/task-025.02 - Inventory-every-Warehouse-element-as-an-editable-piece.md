---
id: TASK-025.02
title: Inventory every Warehouse element as an editable piece
status: Done
assignee: []
created_date: '2026-10-30T16:24:00Z'
updated_date: '2026-10-30T16:51:00Z'
labels:
  - level-editor
  - thps
dependencies:
  - TASK-025.01
references:
  - .tools/thps1/warehouse/warehouse.obj
  - scripts/build_thps_level.py
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
documentation:
  - docs/thps-warehouse.md
  - docs/thps-warehouse-layout.md
  - docs/thps-warehouse-pieces.md
modified_files:
  - docs/thps-warehouse-pieces.md
  - scripts/check_thps_piece_inventory.py
  - tests/test_thps_piece_inventory.py
  - docs/thps-warehouse.md
  - docs/thps-warehouse-layout.md
  - docs/development.md
  - AGENTS.md
parent_task_id: TASK-025
type: task
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The extracted OBJ carries roughly 252 object groups, but the pack importer discards those boundaries and merges faces by material, so the shipped mesh has no notion of a piece at all. Before anything can be exposed in the editor, someone has to decide what the pieces are: which groups form the taxi, which faces are the glass box walls and individual windows, where each half pipe and quarter pipe section begins and ends, and which script-injected elements need an editable form. Without that inventory, decomposition would be improvised per asset and would leave geometry stranded in an uneditable remainder.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every face of the extracted mesh belongs to exactly one named piece, with no geometry left unassigned
- [x] #2 Each inventory entry names the element in play terms (taxi, glass box wall, individual window, half pipe section, quarter pipe run, deck, ledge, rail, rail post, sign, floor, roof) and records the source OBJ groups or faces behind it
- [x] #3 Script-injected elements — roof, floor patches, rail posts, hidden grind rails, boss portal and its spawn redirect, radio, collectibles, spawn markers and authored level settings — each appear with how they become editable
- [x] #4 Ramp geometry is broken into composable module types, each with its profile, height and how it mates with neighbours
- [x] #5 The inventory is written to a doc under docs/ and checked against the landmarks and structures recorded in docs/thps-warehouse.md
- [x] #6 Docs link the inventory from the existing Warehouse documentation
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Audit all 252 OBJ object declarations, face ordinals, materials and measured world-space bounds against the legacy importer, generator and Warehouse landmark docs. Distinguish empty objects, duplicate/state geometry, individual windows and importer-suppressed rail plates.
2. Write tests first for an additive inventory reader/coverage checker: every source polygon assigned exactly once, selectors resolve, source fingerprint/counts match, names/IDs are unique, and the documented inventory covers script additions and composable ramp profiles.
3. Write docs/thps-warehouse-pieces.md as the authoritative face/group inventory, with separate room walls/windows/floor/roof, ramp transition/deck/flat/hip/corner/end vocabulary, measured profiles and mating rules, and editability mappings for all generator/importer additions and settings. Link it from existing Warehouse docs. Keep all legacy assets and level bytes untouched.
4. Validate inventory coverage and landmark cross-checks, run preservation check and task check, then record evidence and make the required conventional commit. Later tasks implement palette assets, attached behaviour and the separate assembled level; this task only inventories them.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Working tree was clean except this task's status update. Source audit finds 252 object declarations but only 1345 polygon faces; many declarations have zero faces. Several start-area groups duplicate geometry/state variants and the legacy importer includes both. The inventory must retain those explicitly rather than assuming 252 independently placeable objects or silently deduplicating.

Added the authoritative Markdown face partition plus checker and 14 tests (written before their implementation/fixes). Exact coverage passes for all 1345 polygons and all 52 empty declarations. Geometry audit also distinguishes the main half pipe's outer sloped banks from horizontal decks, and its tapered sloping apron from a flat bottom; start duplicate groups retain both variants. Source audit is not future-kit live verification.

User additionally requested correcting Python test documentation after introducing pyproject.toml. Verified uv documentation: optional test extras require explicit --extra test, making --with pytest/runtime packages redundant for project test runs. Updated docs/development.md and AGENTS.md pointer; documented existing Taskfile wrapper's legacy flags without changing its command. pytest.ini still takes precedence over pyproject pytest settings. Focused inventory tests pass (14); task check running.

Final evidence: docs/thps-warehouse-pieces.md contains 214 named source pieces covering exactly 1345 faces, literal source group/face selectors, the 52 empty objects, ramp profile/mating/pivot contract, all importer and generator additions (including 10 posts and all 32 hidden rails), and an M1–M15/reference-structure cross-check. Both existing Warehouse docs link it. Source coverage CLI and standalone preservation CLI pass. task check passes (1392 C# tests, 579 Python tests, build, markdownlint/ruff); pre-existing nullable warnings and pytest-asyncio fixture-scope warning remain. Final focused tests pass 14/14 after lint import sorting; final task lint passes after final wording/count refinements. No legacy generator, level, extraction, pack assets, pyproject.toml or uv.lock changed. Ready for conventional implementation commit.

Committed implementation as cfeb629 (docs(thps): inventory editable Warehouse construction pieces), including the requested Python dependency/test command documentation correction. All acceptance criteria and Definition of Done verified. No palette/runtime implementation or next subtask started.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Defined 214 named Warehouse source pieces covering all 1345 OBJ polygons exactly once, accounting separately for 52 empty declarations, duplicate start geometry and suppressed rail remnants. Documented composable ramp profiles/mating rules, individual windows, all importer/generator additions and editable settings, and cross-checked reference landmarks. Added an inventory checker and 14 tests; both existing Warehouse docs link the inventory. Also corrected docs/development.md and AGENTS.md to use uv run --extra test pytest with pyproject.toml/uv.lock, noting pytest.ini precedence and the unchanged legacy Taskfile wrapper. Verification: task check passes (1392 C# tests, 579 Python tests, build and lint), standalone preservation matches, and final focused tests/lint pass. Shipped Warehouse and legacy assets unchanged. Implementation commit cfeb629.
<!-- SECTION:FINAL_SUMMARY:END -->
