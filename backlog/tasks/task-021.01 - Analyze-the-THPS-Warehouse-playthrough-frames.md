---
id: TASK-021.01
title: Analyze the THPS Warehouse playthrough frames
status: Done
assignee:
  - claude
created_date: '2026-10-27T22:08:00Z'
updated_date: '2026-10-27T22:38:00Z'
labels:
  - level-editor
  - thps
dependencies: []
references:
  - tools/thps_warehouse_frames/
  - tools/thps1_100_playthrough.mkv
modified_files:
  - docs/thps-warehouse.md
parent_task_id: TASK-021
priority: medium
type: spike
ordinal: 87000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The warehouse can only be rebuilt faithfully if its 3D geometry is first understood. The only 3D view of it is a 100% playthrough video, extracted to 219 frames at 1 fps (`tools/thps_warehouse_frames/frame_0001.jpg` to `frame_0219.jpg`, video 00:39 to 04:18). Both the frames and the source `tools/thps1_100_playthrough.mkv` are gitignored; regenerate the frames with `ffmpeg -ss 00:39 -to 04:18 -i tools/thps1_100_playthrough.mkv -vf fps=1 -q:v 2 tools/thps_warehouse_frames/frame_%04d.jpg`.

This task reads the frames and records what the level physically contains, so later tasks do not have to re-watch the video. Output goes in a new doc under `docs/` (document content, not task IDs). The map and wiki analysis is a sibling task, TASK-021.02, and adds to the same doc.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A doc under docs/ catalogs each distinct structure seen in the frames: quarter pipes, half pipe, kickers, taxi funbox, big rail, decks, ledges, the glass corridor and secret room, and the two entrances
- [x] #2 Each structure cites the frame numbers that show it best
- [x] #3 Relative sizes and heights are estimated, with the reference used for scale stated
- [x] #4 Surface materials, colors and wall or ceiling details that matter for recreating the look are noted
- [x] #5 Anything the frames cannot resolve is listed explicitly instead of guessed
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
1. Read all 219 frames in three parallel read-only passes (1-73, 74-146, 147-219), logging visible structures, camera position/heading, and scale cues per frame.
2. Verify each structure's best frames by opening them directly before citing.
3. Write docs/thps-warehouse.md: source and regeneration command, remake-vs-original caveat, scale method, one section per structure (cited frames, size/height estimates with stated reference, placement, materials), global look, and an Unresolved list.
4. Add a docs pointer if an index exists.
5. Run task check; verify each AC with evidence; commit docs and backlog close separately, conventional commits, no attribution.
No code changes, so TDD does not apply (doc-only spike).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Read all 219 frames in three parallel passes, then opened the cited best frames directly (1, 4, 9, 10, 12, 24, 71, 100, 110, 119, 138, 156, 172, 188) to confirm the doc's claims. Subagent reports disagreed on SKATE letters (world icons are visible in the flyover, frames 4 and 12) and on the taxi (car shell in 156, faceted mound in 71); resolved from the frames.

Footage is the THPS 1+2 remake, noted in the doc as a caveat.

Doc-only spike: no testable logic, so DoD 2 does not apply. task check exits 0 (276 pytest tests pass, markdownlint and ruff clean).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added docs/thps-warehouse.md. It catalogs the entrances, quarter pipes (wide plywood, wide slotted steel, winding, tall channel, small), half pipe, kickers, taxi funbox, big rail, decks and ledges, glass corridor and secret room, box piles and SKATE letters. Each has cited frame numbers, skater-scale size estimates (skater 1.8 m, cones and barricades as cross-checks) and material notes, followed by a global look section and an explicit Unresolved list (room layout and headings, half pipe extent, taxi identification, corridor versus secret room, exact dimensions, remake-versus-original differences). Footage is the remake, so look notes are remake look.
<!-- SECTION:FINAL_SUMMARY:END -->
