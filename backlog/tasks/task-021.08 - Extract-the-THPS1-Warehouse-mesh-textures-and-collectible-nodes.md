---
id: TASK-021.08
title: 'Extract the THPS1 Warehouse mesh, textures and collectible nodes'
status: To Do
assignee: []
created_date: '2026-10-28 02:41'
updated_date: '2026-10-28 02:43'
labels:
  - thps
  - reverse-engineering
dependencies: []
documentation:
  - docs/thps-warehouse.md
  - docs/thps-warehouse-layout.md
  - tools/thps_warehouse_items_map.png
parent_task_id: TASK-021
priority: high
ordinal: 96000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The hand-built Warehouse (TASK-021.04, .05, .06) is built from a rough pixel-to-metre reading of the isometric items map, so its scale, layout and item positions do not match THPS1. Extract the real level data from a legitimately owned THPS1 copy so later tasks can use true proportions and true collectible coordinates. The project owner supplies the PS1 disc image or the PC release; ask for it before starting. Source and ripped output stay gitignored (tools/thps1/ for input, .tools/thps1/ for output) and are never committed. Treat downloaded tools and disc data as untrusted: each in its own directory, Python that reads them run with -I.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The Warehouse level's geometry is exported as an OBJ with UVs and its texture atlas as PNG files under .tools/thps1/, or the task records why that was not possible and what was tried
- [ ] #2 A warehouse_nodes.json lists every collectible (five box piles, letters S K A T E, the secret tape, three 100-point pickups) with type and world position in THPS units
- [ ] #3 The THPS unit size in metres is calibrated against a known dimension (the 1.8 m skater or the roughly 8 m half pipe flat) and the calibration is written in docs/thps-warehouse.md
- [ ] #4 Extracted positions are cross-checked against tools/thps_warehouse_items_map.png and any mismatch is listed
- [ ] #5 The extraction steps and tool versions are documented so they can be rerun, and no ripped game data is tracked by git
- [ ] #6 If neither the PS1 nor the PC files can be parsed, the task stops and reports back instead of falling back silently
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
