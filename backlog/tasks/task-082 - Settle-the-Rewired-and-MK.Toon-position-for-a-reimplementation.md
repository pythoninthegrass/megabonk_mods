---
id: TASK-082
title: Settle the Rewired and MK.Toon position for a reimplementation
status: To Do
assignee: []
created_date: '2026-11-16 00:31'
labels: []
dependencies: []
references:
  - docs/development.md
modified_files:
  - docs/
  - scripts/
priority: medium
ordinal: 255000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Route C needs two paid third-party packages that the free ones do not cover: Rewired for input and MK.Toon for the toon shading. Neither can be redistributed, so the reimplementation route has a licensing and an asset boundary that the rest of the dependency list does not, and nobody has established what that boundary actually is. The cost of finding out late is a port that cannot be published, which is worse than a port that is slow.

The technical half has a known trap. Rewired's key bindings live in serialized Unity assets rather than in managed code, so they appear in neither the Il2Cpp dump nor in any decompilation and have to be recovered from the shipped assets and confirmed in the running game. Whatever replaces input has to reproduce that behaviour from data, not from a guess at the default map.

Scope is a decision per package, not a migration. Measure the surface the game actually uses, the type and method counts in dump.cs, the serialized assets that reference each package, and what a player would have to own or already owns through the shipped build, then record a verdict of reimplement, vendor under the user's own licence, or substitute an open-source equivalent. Cost matters only after the surface is counted, and an estimate given before the count is the kind of figure this repository has been burned by before.
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
