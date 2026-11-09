---
id: TASK-003.03
title: Undo/redo edit stack over level state
status: Done
assignee: []
created_date: '2026-10-06 21:41'
updated_date: '2026-10-07 20:59'
labels:
  - level-editor
dependencies:
  - TASK-003.02
parent_task_id: TASK-003
priority: high
type: feature
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-003 first for full context.

Implement an in-memory `LevelState` model (pure data: a tile grid plus placed/removed object records) and an `EditStack` that applies TASK-003.02's edit operations to it, with undo/redo:

- `Apply(op)`: mutates (or returns a new, if an immutable-state approach is preferred — decide and be consistent) `LevelState` by applying one edit op, and pushes it onto the undo stack, clearing any redo stack.
- `Undo()`: reverts the most recent op, moving it to the redo stack. Each op type needs a well-defined inverse (e.g. `SetTileHeight`'s inverse restores the previous height — this means ops may need to capture the pre-edit value when applied, not just the target).
- `Redo()`: re-applies the most recently undone op.
- Edge cases: `Undo()` with an empty undo stack is a no-op (not an exception). `Apply(op)` after some undos clears the redo stack (standard undo/redo semantics — a new edit invalidates the "future" that redo would have replayed).

TDD: write tests for single apply, multi-step apply+undo+redo sequences, undo-past-the-start (no-op), and apply-after-undo-clears-redo, before implementing each piece.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 LevelState is a pure data model (tile grid + object records) with no Unity dependencies
- [x] #2 EditStack.Apply correctly mutates/produces LevelState for every op type from TASK-003.02 and pushes an invertible record onto the undo stack
- [x] #3 Undo reverts the most recent edit using a well-defined inverse per op type, verified by tests restoring prior tile heights/slopes and object states
- [x] #4 Redo re-applies an undone edit, verified by tests
- [x] #5 Undo on an empty stack is a no-op, not an exception, verified by a test
- [x] #6 Applying a new edit after one or more undos clears the redo stack, verified by a test
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added `LevelState` (`src/MegabonkLevels.Mod/level_state.cs`): a Unity-free tile grid (`TileState`) plus object-override table (`ObjectState`) keyed by `ObjectTarget`.

Added `EditStack` (`src/MegabonkLevels.Mod/edit_stack.cs`) applying TASK-003.02's seven op types to `LevelState` with undo/redo. Each op's inverse is built by capturing the pre-mutation record (or its absence) before applying, so undo always restores the exact prior state, deleting the key entirely when no record existed before (the correct inverse for a first move/remove on a generator-spawned object, since `LevelState` never knew its generator-assigned transform). `Apply` clears the redo stack; `Undo`/`Redo` return `false` as a no-op on an empty stack rather than throwing. `PlaceObject` allocates one monotonic placement id per `Apply` and reuses it across that op's own undo/redo.

58 tests total (14 new: `tests/MegabonkLevels.Tests/edit_stack_tests.cs`) covering single-apply state per op type, undo/redo restoring exact prior tile/object records, undo-on-empty-stack as no-op, apply-after-undo clearing redo, and a multi-step apply/undo/undo/redo/redo sequence. Docs updated in `docs/level-format.md`.
<!-- SECTION:FINAL_SUMMARY:END -->
