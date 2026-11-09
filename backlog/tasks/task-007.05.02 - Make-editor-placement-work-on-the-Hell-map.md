---
id: TASK-007.05.02
title: Fix Hell level loading (no MapData found)
status: Done
assignee:
  - Claude
created_date: '2026-10-27 05:47'
updated_date: '2026-10-27T19:53:00Z'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-007.05
priority: low
ordinal: 71000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found while verifying TASK-007.05: loading a level with `map: 4` (Hell) logs `LevelLoader: no MapData found for map=Hell` and never starts the map, so the editor cannot be used there. Desert is a ProceduralMesh map and Graveyard a Tiles map that loads; Hell's type is not yet known. Find why `LevelLoader` cannot find Hell's `MapData` (for example it is not loaded until unlocked or has another name) and fix it, then check whether Hell is a Tiles map.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The reason LevelLoader finds no MapData for Hell is identified and documented
- [x] #2 A level with map Hell loads through `run.py relaunch`, or the reason it cannot is documented
- [x] #3 Hell's `EMapType` is recorded; if it is Tiles the kill floor arms and the player has a grid cell, and if it is ProceduralMesh it is refused like Desert
- [x] #4 If Hell is a Tiles map: in the editor, selecting a palette entry and clicking a tile places the object, and undo/redo and save work
- [x] #5 Forest behaviour is unchanged
- [x] #6 Unit tests cover any Unity-free logic added
- [x] #7 `run.py relaunch` into a level whose map fails to start (such as `no MapData found`) fails fast with that reason instead of retrying until timeout
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
1. Diagnose: log every MapData from Resources.FindObjectsOfTypeAll and DataManager.Instance.maps (eMap, name) when the lookup fails, relaunch with a map:4 level, read the log.
2. Fix FindMapData per the finding (likely fall back to DataManager.Instance.maps, or load the asset on demand); keep Forest path unchanged.
3. Record Hell's EMapType; verify kill floor / editor refusal per AC #3, placement/undo/save if Tiles (AC #4).
4. Make relaunch fail fast on a fatal load failure: the mod logs a terminal reason line, scripts/run.py stops on it (tests first in tests/).
5. Document in docs/ (cause, Hell EMapType), run task check, conventional commit without attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Context added 2026-10-27: the editor refusal for non-Tiles maps is in commit d183a25, so if Hell turns out to be ProceduralMesh, AC #3 is already satisfied by it. `run.py relaunch` now stops early only on `KillFloor: armed` or `EditorMode: unsupported map`; a load that fails earlier (`LevelLoader: no MapData found for map=Hell`) emits neither line, so relaunch into Hell still retries five times and times out. Check Hell with `run.py load` plus the log until the loader is fixed.

AC #4 is conditional on Hell being a Tiles map; it is ProceduralMesh (mapType=1), so it does not apply. Verified live: relaunch into map 64 logs `LevelLoader: starting map=Hell` then `EditorMode: unsupported map: MapHell is not a tile map (mapType=1)`. Forest relaunch still enters the editor and arms the kill floor. A relaunch into map 32 stops after one attempt (29s) on `LevelLoader: load failed`.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Cause: the MapHell asset has eMap=64, not the 4 that the Il2Cpp EMap enum (and the mod's EMap) listed, so the loader's value match never found it. MapDungeon (eMap=16) is also loaded, and neither it nor Hell is in DataManager.maps. Fix: mod EMap now mirrors the asset values (Hell=64, Dungeon=16); a load whose MapData is still missing 20s after being queued logs `LevelLoader: load failed: no MapData found ...; available: ...` and is dropped; `run.py relaunch` stops on that line instead of retrying five times. Hell is ProceduralMesh, so the editor refuses it like Desert. Verified: dotnet tests (976) and pytest (227) pass, `task check` exits 0, and live relaunches for Forest, Hell and an unknown map behave as described. Risk: level files saved with map=4 for Hell (none in the repo) no longer load. Commit d3d56ce.
<!-- SECTION:FINAL_SUMMARY:END -->
