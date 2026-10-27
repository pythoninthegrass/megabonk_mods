---
id: TASK-021
title: Recreate the THPS Warehouse as a Megabonk level
status: To Do
assignee: []
created_date: '2026-10-27T22:08:00Z'
updated_date: '2026-10-27T22:08:00Z'
labels:
  - level-editor
  - thps
dependencies: []
references:
  - tools/thps_warehouse_strategywiki.md
  - tools/thps_warehouse_items_map.png
  - tools/thps_warehouse_itemless_map.png
  - tools/thps_warehouse_frames/
priority: medium
type: feature
ordinal: 86000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Goal: rebuild the Tony Hawk's Pro Skater 1 Warehouse as a playable Megabonk custom level, driven by an agent through the `megabonk` MCP server. It proves the editor and MCP tooling can reproduce a known, well-documented layout faithfully, reusing existing game assets where possible and adding new ones only where nothing fits.

Reference material lives in `tools/`. The frames, the video and the maps are gitignored, so they only exist on machines that have them:
- `tools/thps_warehouse_frames/frame_0001.jpg` to `frame_0219.jpg`: 1 fps frames from a 100% playthrough (video 00:39 to 04:18). Regenerate from `tools/thps1_100_playthrough.mkv` with `ffmpeg -ss 00:39 -to 04:18 -i tools/thps1_100_playthrough.mkv -vf fps=1 -q:v 2 tools/thps_warehouse_frames/frame_%04d.jpg`.
- `tools/thps_warehouse_items_map.png` and `tools/thps_warehouse_itemless_map.png`: top-down maps with and without collectibles.
- `tools/thps_warehouse_strategywiki.md`: the StrategyWiki guide (gaps, SKATE letters, secret tape, 100-point pickups, five box piles). Not gitignored.

Collectibles are not recreated as THPS pickups. They stay normal in-game Megabonk items (chests, shrines and similar) placed where the matching THPS item sits. The level should also play its own music, which needs new research because the game's music path has not been analyzed.

Subtasks are sequential phases: analysis, layout spec, geometry, new assets, item placement, music.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The level loads from a saved level file and is playable through a run
- [ ] #2 Its layout matches the THPS reference material, confirmed by side-by-side screenshots
- [ ] #3 Megabonk items sit at the spots where THPS collectibles are
- [ ] #4 The level plays its own music instead of the stock track
- [ ] #5 All subtasks are done
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
