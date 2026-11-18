---
id: TASK-084
title: Determine PS Vita viability and deliver a full native Megabonk port on GO
status: To Do
assignee: []
created_date: '2026-11-18T06:01:00Z'
updated_date: '2026-11-18T06:06:00Z'
labels:
  - ps-vita
  - native-port
dependencies: []
references:
  - TASK-080.12.06
  - TASK-080.13
  - TASK-081
  - 'https://github.com/pythoninthegrass/vita_ssh'
documentation:
  - .agents/skills/vita-port/SKILL.md
  - docs/performance.md
  - docs/development.md
type: feature
ordinal: 285000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Target the physical PCH-2000 with a native reimplementation. The shipped x86-64 Unity IL2CPP player has no matching Vita runtime; the arm64 lift is neither a prerequisite nor the delivery route. Use a pinned, legitimately owned shipped build as the behavioral reference. OpenBonk is a second reference, not a Vita engine; only reuse code or assets with verified rights. Keep game-derived inputs and outputs local-only and do not bundle proprietary game data or Sony modules.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A bounded prototype and on-device measurements produce a recorded GO or NO-GO verdict; full-port subtasks require an explicit GO, not just a Done dependency.
- [ ] #2 On GO, deliver the complete offline base game for the pinned reference build as a native, locally reproducible PCH-2000 VPK, with hardware performance and gameplay/content parity verified.
- [ ] #3 On NO-GO, stop port work, mark every post-gate subtask Done with every acceptance criterion unchecked, and record 'Not implemented — NO-GO' with a link to the gate evidence on each. Close this parent with the full-port criterion unchecked; do not claim delivery.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Hardware iteration: vita_ssh is the maintainer's public PS Vita tooling project, designed for rapid on-device iteration. It provides Vita-specific equivalents for common shell operations and a fully ported OpenSSH server. Use the upstream repository link for discovery and setup rather than assuming a checkout path. It is a development aid, not a runtime dependency of the port.
<!-- SECTION:NOTES:END -->
