---
id: TASK-077
title: >-
  Pack loose uniforms into named uniform blocks for the 49 shader programs Metal
  rejects
status: To Do
assignee: []
created_date: '2026-11-15 23:53'
labels: []
dependencies: []
references:
  - docs/development.md
  - scripts/shader_metal_pass.py
modified_files:
  - scripts/shader_metal_pass.py
  - tests/
  - docs/development.md
priority: medium
ordinal: 250000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The Metal translation pass reaches 99.33 percent (7305 glslang parses, 7305 spirv-cross outputs, 7256 Metal compiles) and the whole 49-program tail sits in 5 shader assets. 48 of them fail for one reason: they declare 33 to 48 loose uniforms and Metal allows 31 uniform-block slots, so the uniforms have to be grouped into named blocks.

One program fails differently: the geometry shader's unknown return type, which no MSL target supports.

Earlier notes rejected automatic block packing because glslang refuses anonymous blocks and a fixed group size breaks on a 48-member shader. What has not been tried is deriving the grouping from the authored Cg source rather than the decompiled GLSL, which is the level the split should happen at.

Out of scope: blend state, depth conventions and culling, which metal -c does not check and which stay on the playtest list.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every one of the 49 programs is classified with its exact reason and its authored Cg origin
- [ ] #2 The 48 loose-uniform programs compile to Metal after grouping, or each survivor names a concrete reason it cannot
- [ ] #3 The geometry shader outcome is recorded as pass or as an accepted exclusion rather than a silent gap
- [ ] #4 The pass rate artifact reports the tail as zero or explains each remaining program
- [ ] #5 The pass reruns from a clean out directory and the prior 7256 result does not regress
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
- [ ] #5 No hostname or username or home path appears in tracked files
- [ ] #6 task check passes
<!-- DOD:END -->
