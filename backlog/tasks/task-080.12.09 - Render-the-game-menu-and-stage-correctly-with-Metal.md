---
id: TASK-080.12.09
title: Render the game menu and stage correctly with Metal
status: To Do
assignee: []
created_date: '2026-11-16T19:05:00Z'
labels:
  - native-macos
  - arm64
dependencies:
  - TASK-080.12.08
  - TASK-077
references:
  - TASK-077
  - scripts/shader_metal_pass.py
documentation:
  - docs/development.md
parent_task_id: TASK-080.12
priority: high
type: enhancement
ordinal: 276000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Shader compilation is not shader integration: translated programs can compile and still bind the wrong uniforms or render with incorrect depth, culling or blend behaviour. This task consumes the headless native game and TASK-077's shader-tail outcomes, installs the usable Metal shader representation into the native player and validates real frames. An accepted exclusion in the shader spike is not automatically acceptable if gameplay needs that shader.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The native arm64 game renders its menu and a representative playable stage through Metal using the shipped materials and documented shader replacements.
- [ ] #2 All shader-tail outcomes from TASK-077 are resolved for actual game use or shown not to affect supported scenes; required shaders never silently fall back to pink/error output.
- [ ] #3 Captured frames and explicit checks cover text, transparency, water, lighting, depth and culling against the shipped reference, documenting intentional backend differences.
- [ ] #4 A reproducible rendering smoke check and docs describe shader provenance, material/binding coverage and remaining visual limitations.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
