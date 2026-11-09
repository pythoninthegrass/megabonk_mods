---
id: TASK-025.01
title: Record a preservation baseline for the shipped Warehouse level
status: Done
assignee:
  - '@opencode'
created_date: '2026-10-30T16:24:00Z'
updated_date: '2026-10-30T16:32:00Z'
labels:
  - level-editor
  - thps
dependencies: []
references:
  - scripts/build_thps_level.py
  - levels/thps.mblevel.json
  - scripts/thps_item_overrides.json
documentation:
  - docs/development.md
  - docs/asset-bundles.md
modified_files:
  - scripts/check_thps_preservation.py
  - tests/test_thps_preservation.py
  - tests/fixtures/thps-preservation.json
  - docs/development.md
parent_task_id: TASK-025
type: chore
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The construction kit work will add pack assets, change the generator and touch the editor's handling of placed objects, all while levels/thps.mblevel.json and the assets it loads must stay exactly as they are. Without a machine-checkable baseline there is no way to prove later tasks did not disturb the shipped level, and a byte drift in a generated level file is invisible in review. This task establishes that baseline and the check that enforces it, before any decomposition work starts.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A committed baseline records the current levels/thps.mblevel.json contents, the generator's derived values, and the pack assets the level depends on
- [x] #2 A check compares the level file, a fresh generator run's output and the pack asset inventory against the baseline and fails naming every difference
- [x] #3 Regenerating with scripts/build_thps_level.py reproduces the baselined level file exactly
- [x] #4 The check runs in the existing test suite and passes before any decomposition work lands
- [x] #5 Docs state how to refresh the baseline deliberately and that a refresh means the shipped level changed
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
1. Write failing tests for a preservation snapshot/comparison tool: byte-exact level and fresh generator output, derived placement/collectible/rail values, required pack entries, and per-file asset fingerprints; report all differences and reject missing prerequisites.
2. Commit a JSON baseline containing the shipped level text, derived values, and inventory/hashes of legacy Warehouse geometry, collision, materials, textures, importer metadata, default music, and extraction inputs. Allow unrelated additive assets; do not pin the whole bundle or builder source because later tasks extend them. Run the generator in a fresh process into a temporary directory, never over the shipped file.
3. Integrate the check into pytest, exercise changed/missing/additive inventory cases, and document strict prerequisites and intentional refresh semantics.
4. Verify byte-identical regeneration, run task check, review all changes and make the required conventional commit; finalize only with objective evidence.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Working tree was clean before the task status update. Local extraction, generated Unity Assets/Thps files, soundtrack and both bundles exist. Existing tests already require the extraction for build_level; the preservation check will fail explicitly when required source/generated assets are absent rather than silently skipping. Whole bundle hashes would incorrectly forbid additive pack work, so the baseline protects individual legacy asset files instead.

Implemented baseline with full level text, derived placements/rails/collectibles, required prefab/music references, and 432 source/generated asset fingerprints. Added 10 tests covering baseline matching, all-difference diagnostics, byte-only drift, changed/missing files, additive manifest assets, independent generator comparison, missing extraction/generator failures, CLI non-mutation, and refresh refusal. Initial tests failed at import before implementation; focused tests now pass (10/10). First task check passed: 1392 C# + 562 Python tests, build and lint. Added three final failure-path tests afterward; final task check is running.

Confirmed levels/thps.mblevel.json is identical to HEAD (SHA-256 c74ffeb46811ea78c37c9577600e814510ff0719d91adc57e4702f4716ee5be9). Generator and legacy pack assets were not edited. Check requires prepared gitignored extraction, soundtrack and Unity assets, and compares generated files rather than installed bundle contents; docs explicitly require rebuilding after pack-authoring changes.

Final task check passed: clean mod build (0 warnings/errors), 1392 C# tests and 565 Python tests, markdownlint and ruff. Standalone preservation CLI also passes. Committed implementation and baseline as 41659a6 (test(thps): baseline shipped Warehouse preservation). All five acceptance criteria verified: baseline contents/inventory, difference/failure-path tests, fresh-process byte-identical generation, existing-suite integration, and documented refresh procedure. No decomposition work started.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added a committed Warehouse preservation baseline containing exact level text, generator-derived values and 432 legacy source/generated asset fingerprints. Added a standalone strict check and 10 pytest tests; fresh generation runs into a temporary path and compares bytes without modifying the shipped level. Documented preparation, coverage limits and deliberate refresh semantics. Existing Warehouse level and assets remain unchanged; additive pack assets remain possible. Verified task check: build, 1392 C# tests, 565 Python tests and lint all pass. Implementation commit: 41659a6.
<!-- SECTION:FINAL_SUMMARY:END -->
