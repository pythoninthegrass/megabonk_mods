---
id: TASK-086.03.02
title: Rebuild the BSP faithfully with ordered additive and subtractive operations
status: In Progress
assignee: []
created_date: '2026-11-27 18:27'
updated_date: '2026-11-28T06:28:00Z'
labels:
  - level
  - kf1
dependencies:
  - TASK-086.03.01
documentation:
  - docs/kf1-mountain-pass.md
parent_task_id: TASK-086.03
priority: low
ordinal: 305000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Second, faithful version of the BSP: apply the additive and subtractive `Brush` actors in level order (the order they appear in the exported T3D) with a mesh boolean library, so rooms and doorways carved by subtractive brushes are reproduced and hidden interior faces are removed. Replaces the approximate geometry from the first subtask once it is correct; compare the two in the running game and keep the approximate result if the boolean output is unreliable on any brush. Check the result is watertight enough for the collision mesh and does not slow level load noticeably.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Subtractive brushes carve the additive geometry in level order, and unit tests cover a carved box and a doorway
- [x] #2 Interior faces hidden by the boolean operations are removed from the render mesh
- [ ] #3 A before-and-after screenshot of a building interior from the running game shows the difference from the approximate version
- [ ] #4 Load time and collision behavior are checked and any brush that fails falls back to the approximate geometry
- [x] #5 The five all-black six-face solids (Brush23, Brush39, Brush173, Brush186, Brush245) are resolved against the compiled map: faces that survive ordered subtraction are restored to the render mesh and collision, or their omission is justified in docs/kf1-mountain-pass.md
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Ordered CSG rebuild of the Mountain Pass brush world, in scripts/kf1_bsp.py plus hooks in scripts/kf1_mountain_pass.py.

Engine (probed on the real export, not assumed): manifold3d 3.5.4 (pulls numpy). Validated on KF-MountainPass.t3d: booleans are exact (union of two half-overlapping boxes gives volume 120 and difference 56 against analytic values), hidden faces are dropped (real brush pairs union to fewer triangles than the sum, 20 vs 24), a carve reduces volume by the cutter exactly (Brush351 51,775,488 minus Brush9 41,796,608 leaves 9,978,880), and the whole 461-brush fold runs in 0.1 s at 94 MB.

Steps, test-first:
1. Extend the brush parser to keep every CSG operand in T3D actor order: op (CSG_Add/CSG_Subtract), per-polygon Normal, Origin, TextureU/V, Vertex, plus actor Location/PrePivot. Keep the existing parser test green.
2. Brush solid: fan-triangulate each polygon, flip the fan when its geometric normal disagrees with the exported Normal (the export winds some polygons backwards), weld corners by rounded position, build the Manifold. Failing status or non-positive volume marks the brush uncarvable.
3. Fold in level order: additive brushes merge into overlapping components (union-find by bounding box, batch union); a subtractive brush cuts only components that already exist and overlap it. Consequence to document: Brush10, the single world-size subtractive sitting second in the file, carves nothing because nothing exists yet; subtracting it later would delete the map, which is why the approximate pass skipped it too.
4. Attribution back to textures: carry the source polygon index as a Manifold vertex property; a triangle whose three corners share one integer index is attributed exactly, otherwise fall back to matching the triangle plane against that component's member brushes and then to the existing baseColor fallback.
5. Emit into the existing mesh.json shape: same primitives, materials and shared collision arrays, so unity/pack-authoring/Assets/Editor/Kf1MountainPassPack.cs needs no change. Simplify each component and assert volume is unchanged.
6. prepare gains a mode switch so the same converter emits the approximate and the faithful mesh, which is how the before-and-after screenshots are taken without keeping two code paths.
7. Fallback per AC4: uncarvable brushes keep today's fan triangulation. Census from the export: 424 of 462 close as solids; the 38 that do not are open shells (every failed edge count is odd, no doubled edges), which includes the 17 portal sheets and Brush173, Brush186 and Brush245 of the five all-black solids. Open shells cannot be carved, which is worth stating in the docs.
8. Re-check what the carve does to placement grounding: make_level derives floors from the collision array, so the three shops and the eight shrine candidates must still ground; prepare prints the skipped list.
9. Five all-black solids: report which faces of Brush23, Brush39, Brush173, Brush186 and Brush245 survive, keep the survivors only if they are not uncarved walls across playable space, and write the answer in docs/kf1-mountain-pass.md.
10. In game: rebuild the pack, load both modes, screenshot one building interior each, and record the collision decision plus triangle counts for AC4.

Risks: open shells stay uncarvable and keep their uncarved interior faces; attribution needs the plane fallback for cut triangles (85% matched globally in the probe, better once restricted to a component); carving changes floors under the shop and shrine spots; AC3 needs Unity 2023.2.22f1 on the build box and a relaunch on the player box.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Handed off mid-task: implementation done, unit-tested, run against the real export; the in-game check is what is left.

**Implemented**
- `scripts/kf1_bsp.py` (new): `compile_brushes(brushes) -> Compiled(triangles, uncarved, cutters, estimated)`. Brushes fold in T3D actor order; additive union merges components on contact (`_touching`, inclusive), subtractive `Difference` runs only against overlapping components (`_overlapping`, strict), so a cutter that arrives before the geometry it would cut is a no-op. Each brush is welded to 4 decimals into `manifold3d` first (a raw triangle soup returns `Error.NotManifold`); fan winding is corrected against the exported `Normal`. Output faces are attributed to source polygons by plane plus polygon outline, preferring additive over subtractive, with a nearest-face fallback counted in `estimated`.
- `scripts/kf1_mountain_pass.py`: `parse_brushes` now returns `{name, op, offset, faces}` with a per-face `Normal` and keeps subtractives in level order; `unpack_map(..., brushes=(), csg=False, compiled=None)`, `prepare(..., csg=False) -> (level, skipped, compiled)`, `main` gained `--csg` and prints the census. `append_compiled` emits one mesh per brush, named after the cutter when the skin came from a subtraction.
- `tests/test_kf1_bsp.py` (new, 17 tests, written first): level-order dependence, sealed-then-carved room, doorway, touching brushes share one skin (no stacked coplanar faces), enclosed carve keeps both wall sets, per-brush fallback, cut-surface texture attribution, and both `unpack_map` passes reaching render and collision. Green, along with the 51 existing `tests/test_kf1_mountain_pass.py`.
- Real export: `uv run python scripts/kf1_mountain_pass.py prepare --csg` folds 461 brushes into 7,736 skin triangles (1,236 of them from subtractive polygons), 32 estimated attributions, 38 uncarved brushes falling back individually, 0 dropped cutters, about 8 s against 5 s.
- AC5 answered from measurement in `docs/kf1-mountain-pass.md`: `Brush173`, `Brush186`, `Brush245` never enclose a volume (`Error.NotManifold`) so they are sheets, not solids; `Brush23` and `Brush39` close, survive the fold whole, are not overlapped by any later subtractive, and add their full volume (1,786,511,360 and 486,064,128 cubic units) to the world built without them, so no face of theirs is hidden by a neighbour. Their omission stays justified in the docs; whether KF1 itself blocks the player at those two boxes is unverified and needs a KF1 install to walk up to them.

**State on disk — read before building anything**
- `.tools/kf1/mesh.json` currently holds the **compiled** map (2,235 meshes, 346,723 brush triangles, against 345 / 4,784 approximate), because `prepare --csg` was the last run. Backups: `.tools/kf1/mesh-approximate.json` and `.tools/kf1/mesh-csg.json`. `prepare` without `--csg` regenerates the approximate bytes exactly (`cmp` clean), so switching back is one command, and `task kf1:pack` builds whatever `mesh.json` holds.
- Nothing is committed. `git status`: `scripts/kf1_bsp.py`, `tests/test_kf1_bsp.py`, edits to `scripts/kf1_mountain_pass.py` and `docs/kf1-mountain-pass.md`, and the `pyproject.toml` / `uv.lock` dependency pair (`manifold3d>=3.5,<4`, `numpy>=2.5`, installed with `uv sync`).
- `uv run ruff format` still needs one pass over `tests/test_kf1_bsp.py` (the other touched files are already formatted); `task check` has not been run yet.

**Next steps**
1. `uv run ruff format tests/test_kf1_bsp.py`, then `task check`.
2. Decide the default. Recommendation: keep `--csg` opt-in and ship the approximate map until the game proves the compiled one; flip `prepare`'s default in its own commit afterwards.
3. `task kf1:pack` (incremental, reads `.tools/kf1/mesh.json`) then `task kf1:install`, then `uv run scripts/run.py relaunch` or the `megabonk` MCP tools. AC3: the same building interior before (`mesh-approximate.json`) and after (`mesh-csg.json`), camera flown inside. AC4: load time from the harness log, and walk the compiled map to feel collision, including the `Brush10` no-op and the 38 fallback brushes.
4. If the compiled map wins, delete the two backups, flip the default, and update "Converting the export" in `docs/kf1-mountain-pass.md` to name `--csg` as the shipped path.

**Gotchas learned the expensive way**
- `manifold3d`'s `original_id` is per boolean run, not per source face — do not plan around it, match planes.
- Weld first or every `Csg_Add` brush fails `Error.NotManifold`; 38 still fail because their exported rings do not close.
- Union must include merely-touching brushes, otherwise a wall standing on a floor stacks two coplanar skins and a ray through an opening reads four hits instead of two. The ray helper in the tests dedupes hit distances for that reason.
- `mesh.json` invariants the Unity importer relies on: `meshes[0]` is Terrain with `"uv": []`; brush primitives carry 2 floats per vertex in `uv` (`len(uv) * 3 == len(positions) * 2`); `materials[0]` is the unnamed default; a mesh with no `"source"` is Terrain only.
- pytest here gets `-n` from `addopts`; do not add `-p no:xdist`, and use `-p no:randomly` for stable ordering.

**Update 2026-11-27**
- `ruff format` applied; `task check` passes (3,076 tests).
- The license error was Unity Hub not running; `open -a "Unity Hub"` cleared it (documented in docs/development.md).
- AC3 done: Brush9 corridor screenshots in `.tools/evidence/kf1-interior-csg-3.png` and `kf1-interior-approx.png`.
- AC4 partial: the player settles on the compiled floor; in-game load time and wall collision across other rooms are not measured. `prepare` default stays approximate; `.tools/kf1/mesh.json` holds the compiled map.

Update 2026-11-28
- Fixed since the handoff: the collision mesh used 16-bit indices with about 90,000 vertices, so brush floors past vertex 65535 were missing from the collider and the player fell through them (Kf1MountainPassPack.cs now uses 32-bit indices); brush textures exported into group folders are found; hand-picked vertex colors are stored linear because the vertex tint shader writes them unconverted (the terrain rendered pale before).
- AC3 is unchecked: the Brush9 screenshots were taken near the road end, not in a building interior, and predate the fixes above. Redo the comparison in a real interior with the current build.
- AC4 is partial: the player lands on the compiled floor at the first shop volume; in-game load time, walking the other carved rooms, the Brush10 no-op and the 38 fallback brushes are not checked.
- The first shop volume is a sealed room with no exit (door movers are not in the BSP export). The fidelity gaps and reachable-spot work moved to a follow-up task.
- `prepare` still defaults to the approximate map; flipping it to --csg is not done.
<!-- SECTION:NOTES:END -->
