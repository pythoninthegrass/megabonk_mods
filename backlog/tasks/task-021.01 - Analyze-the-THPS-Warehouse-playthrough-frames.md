---
id: TASK-021.01
title: Analyze the THPS Warehouse playthrough frames
status: To Do
assignee: []
created_date: '2026-10-27T22:08:00Z'
labels:
  - level-editor
  - thps
dependencies: []
references:
  - tools/thps_warehouse_frames/
  - tools/thps1_100_playthrough.mkv
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
- [ ] #1 A doc under docs/ catalogs each distinct structure seen in the frames: quarter pipes, half pipe, kickers, taxi funbox, big rail, decks, ledges, the glass corridor and secret room, and the two entrances
- [ ] #2 Each structure cites the frame numbers that show it best
- [ ] #3 Relative sizes and heights are estimated, with the reference used for scale stated
- [ ] #4 Surface materials, colors and wall or ceiling details that matter for recreating the look are noted
- [ ] #5 Anything the frames cannot resolve is listed explicitly instead of guessed
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
