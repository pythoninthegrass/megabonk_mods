---
id: TASK-003.03
title: Undo/redo edit stack over level state
status: To Do
assignee: []
created_date: '2026-10-06 21:41'
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
- [ ] #1 LevelState is a pure data model (tile grid + object records) with no Unity dependencies
- [ ] #2 EditStack.Apply correctly mutates/produces LevelState for every op type from TASK-003.02 and pushes an invertible record onto the undo stack
- [ ] #3 Undo reverts the most recent edit using a well-defined inverse per op type, verified by tests restoring prior tile heights/slopes and object states
- [ ] #4 Redo re-applies an undone edit, verified by tests
- [ ] #5 Undo on an empty stack is a no-op, not an exception, verified by a test
- [ ] #6 Applying a new edit after one or more undos clears the redo stack, verified by a test
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
