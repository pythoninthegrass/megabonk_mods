---
id: TASK-021.08
title: 'Extract the THPS1 Warehouse mesh, textures and collectible nodes'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-28 02:41'
updated_date: '2026-10-28 03:26'
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
- [x] #1 The Warehouse level's geometry is exported as an OBJ with UVs and its texture atlas as PNG files under .tools/thps1/, or the task records why that was not possible and what was tried
- [x] #2 A warehouse_nodes.json lists every collectible (five box piles, letters S K A T E, the secret tape, three 100-point pickups) with type and world position in THPS units
- [x] #3 The THPS unit size in metres is calibrated against a known dimension (the 1.8 m skater or the roughly 8 m half pipe flat) and the calibration is written in docs/thps-warehouse.md
- [x] #4 Extracted positions are cross-checked against tools/thps_warehouse_items_map.png and any mismatch is listed
- [x] #5 The extraction steps and tool versions are documented so they can be rerun, and no ripped game data is tracked by git
- [x] #6 If neither the PS1 nor the PC files can be parsed, the task stops and reports back instead of falling back silently
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Calibrate the unit on the half pipe (measured from the mesh cross-section; 18 m per unit with 8 m taken as coping to coping, single anchor, low confidence, written in docs/thps-warehouse.md). Done.
2. Tests first (tests/test_thps1_extract.py): CD.HED parsing, ISO sector and directory reading, converter patch, UV normalisation, single material library, TRG node extraction. Done, 18 pass.
3. scripts/thps1_extract.py: disc to CD.WAD to skware files, patched converter run, OBJ with normalised UVs, one MTL, PNGs and warehouse_nodes.json under .tools/thps1/warehouse/. Done, verified end to end on the disc.
4. docs/thps-warehouse.md: extraction steps and pins, format notes, node table, map cross-check, calibration. Done.
5. Confirm no ripped data is tracked. Done. Conventional commit without attribution. Done (3d5727c).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Disc: raw MODE2/2352 BIN, verified as the standard USA SLUS-00860 dump (data track sha1 84fb50dd..., boot EXE sha256 57563b70...). ISO9660 files are read with a small stdlib reader (24 byte sector header, 2048 byte user data). Levels are inside CD.WAD, indexed by CD.HED: entries are a NUL-terminated name padded to 4 bytes, then u32 byte offset and u32 size into CD.WAD. 669 entries.

Warehouse files (skware family, extracted to .tools/thps1/skware/): skware.psx (level model, 131124 B), skware_2.psx, skware_l.psx (240836 B, different layout, not yet identified), skware_o.psx (10612 B, header resembles a model file), skware_t.trg (10590 B, '_TRG' magic, offset table, the node/script data).

skware.psx is the version 4 PSX format (header u16 4, u16 2, u32 tag chunk pointer). Own stdlib parser (scratchpad psxparse.py) parses objects (36 B each, s7.24 positions), models (s3.12 vertices and normals) and faces with every face ending exactly at its length field: 252 objects, 288 models, 1869 faces, 3390 vertices, 89 texture names, tags RGBs and blockmap (0x0A, 20x20 cells). Format reference: GreaseMonkey's public domain gist and the MIT licensed JayFoxRox/thps2-tools convert-psx.py and disassemble-trg.py, read but not executed (the harness denied running downloaded code).

Open: palettes and texture pixel data are not in skware.psx (the 4bpp and 8bpp palette counts and the texture offset count read as 0), so they live in another file (candidates: skware_l.psx, level.pre, a shared texture file). Provisional scale: world extents 2.0 x 2.3 x 3.1 units, so about 7 m per unit if the long axis is the 22 m room length; not yet calibrated against the skater or the half pipe. TRG node parse not started.

alexbeavs-ps1-ports/tony-hawk-s-pro-skater-recomp was checked: a recompilation build scaffold with auto-scanned boot EXE JAL targets and no level format or data knowledge. Useful only for the disc hashes.

Ran JayFoxRox/thps2-tools convert-psx.py and disassemble-trg.py (MIT, read first, then run in .tools/thps1/skware_out/ under bypass permissions). convert-psx.py output matches the own parser exactly: 252 objects, 288 models, world extents x 0.52..2.52, y -1.70..0.62, z 0.40..3.53, 0 palettes and 0 textures in skware.psx; it wrote world.obj (3003 v, 1345 f, no UVs or materials). disassemble-trg.py parsed skware_t.trg into 1637 lines (trg.txt) without errors; its thps1_file flag is False and was not toggled, so some THPS1 specific fields may be decoded with the THPS2 layout.

Collectible nodes in the TRG (position = raw s19.12 / 4096, same units as the model coordinates, y negative is up): SPickup (0.829, -0.104, 2.662), KPickup (1.620, -0.255, 3.481), APickup (1.873, -0.104, 2.962), TPickup (1.893, -0.232, 2.297), EPickup (1.021, -0.152, 1.383), TapePickup (2.238, -0.251, 2.297), BonusPickup100 x3 at (1.893, -0.255, 1.632), (1.395, -0.255, 1.632), (0.921, -0.255, 3.234). A further 100/200/500 cluster sits at x 1.44..1.59, y -0.386, z 0.916 and is not on the items map.

Validation: a 3D affine fit of the six letter and tape positions to their pixel positions on tools/thps_warehouse_items_map.png has errors of 1 to 14 px; the three 100 pickups predict (553,296), (633,373), (342,638) against map markers N (570,303), E (668,382), S (398,686), so the north, east and south 100s are the first, second and third BonusPickup100 above. Fitted scale on the map is about 223 to 259 px per unit on the floor axes.

Box piles: no PowrUp node. The TRG has 45 Crate nodes that carry only a model name hash; 43 resolve to placed objects in skware.psx (positions x 0.52..2.42, y -0.69..0.50, z 0.40..3.28). Which of these form the five box piles on the map is not yet decided.

Still open: texture and palette data location, unit calibration in metres (the 7 m per unit estimate is unconfirmed), mapping crates to the five box piles, the thps1_file flag, OBJ with UVs.

Correction: the note above saying convert-psx.py and disassemble-trg.py were read but not executed is out of date. The first run was denied by the permission classifier; both scripts were run after permissions were relaxed, as recorded in the following notes.

Textures found: skware_l.psx (not level.pre, which is a PRE archive of UI BMPs) is the texture file. It is the same v4 PSX container with 0 objects and 0 models, and holds 99 texture names, 72 4bpp palettes, 25 8bpp palettes and 99 textures (49 at 16 colours... counted over the first 73, 24 at 256). convert-psx.py stops at texture 72 (54x54, 4bpp) with 'BROKEN -56 bytes' because it rounds the height up to a multiple of 4 as well as the width. The THPS1 layout aligns only the width (4bpp to 4 px, 8bpp to 2 px) and keeps the true height. With aligned_height = height (copy in the session scratchpad, vetted script untouched) all 99 textures decode, every texture offset lands exactly, and the PNGs look right on a contact sheet (Shorty's, Toy Machine, crates, bricks, chains, FRAGILE crate). Magenta is the transparency key. Output: .tools/thps1/skware_l_out/out/<NAME-HASH>-0.png plus .mtl per texture; names are the same u32 hashes as the texture-name table in skware.psx.

Correction: world.obj from convert-psx.py is not UV-less. It has 4876 vt lines (raw u8 pixel coordinates, not normalised) and 1345 usemtl lines, 80 distinct material hashes plus None. All 80 hashes have a PNG in skware_l_out/out, so the OBJ only needs its UVs divided by the texture size (v flipped) and the PNGs beside it. The earlier 'no UVs or materials' note was wrong.

thps1_file flag: it is read in one place only, the TrickOb branch for a 14 byte gap (assumed_gap == 14). Re-running disassemble-trg.py with the flag True gives byte-identical output (1637 lines, no errors) and the 'THPS2 ' marker never appears, so that branch is not reached in skware_t.trg and the flag does not affect this file. The pickup positions stand.

Box piles resolved. The 45 'Crate' nodes are breakable props (glass panes, panels, signs: sizes like 0.75 x 0.79 x 1.27, 0.0 x 0.37 x 0.57), not the wooden crates, so they are not the piles. The five piles are the five type 1 'Baddy' nodes whose script ends in C_GOALCOUNTER(0) (nodes 43, 107, 109, 111, 113): (2.023, -0.381, 0.924), (0.896, -0.138, 1.346), (0.616, -0.078, 2.140), (1.318, -0.138, 3.188), (2.460, -0.078, 2.844). Three of them have a cluster of 0xFF05 Baddy nodes within about 0.05 units (debris pieces). Cross-check: an affine fit of 9 items (S K A T E, tape, three 100s) to the map has 5 to 32 px error; the five pile nodes project to (708,167), (810,453), (678,611), (311,612), (172,380) and each lands 16 to 34 px from a different one of the five red circles on the map at (698,155), (790,457), (695,600), (330,614), (199,401). One to one match, no map circle left over. The 100/200/500 cluster at (1.44..1.59, -0.386, 0.916) is real but not on the map.

Unit calibration is NOT done. Measured anchors, all in the OBJ unit: skater (hawk.psx, 19 objects) 0.844 tall, 0.194 wide; c_taxi.psx vehicle 2.53 long, 0.70 wide, 0.61 tall; Warehouse room 2.0 x 3.1 extent. Skater and taxi agree with each other (1.8 m skater gives about 2.1 m per unit, a 4.9 m taxi about 1.9 m per unit), but at that scale the Warehouse would be about 4 x 7 m, so skater and vehicle models are not in the level's unit (they look about 4x larger relative to the level). A level-side anchor is needed. Candidates seen in the level mesh: the two half pipe side pieces (models 8 and 9) sit at z 2.043 and 2.551, 0.508 apart, with the flat floor between them; cardboard heap pieces 0.08 to 0.11 across; a taxi-sized object was not identified (the A letter sits over the taxi at (1.87, -0.10, 2.96), but the objects there are 0.2 or less). The docs figure of about 8 m flat is itself a low-confidence single-anchor estimate, so calibrating on it alone would just restate it. Not yet decided how to calibrate.

Implemented scripts/thps1_extract.py (tests first, 18 pass, ruff format clean) and ran it end to end from the disc into .tools/thps1/warehouse/: 99 PNGs, warehouse.obj (79 materials, 4876 UVs, tiling UVs run past 0..1 so import needs repeat wrapping), warehouse.mtl and warehouse_nodes.json (5 box piles, 5 letters, 1 tape, 6 bonus pickups). The mesh is byte-identical to the earlier manual run. Docs added to docs/thps-warehouse.md (Extracted game data). Half pipe measured at x = 2.018: flat floor z 2.218 to 2.376 (0.158), coping lines z 2.075 and 2.519 (0.444 apart), transition height 0.135. Calibration figure still open: 8 m on the flat gives about 51 m per unit and 6.8 m transitions, which contradicts the docs' 2.5 to 3 m transitions; 8 m coping to coping gives about 18 m per unit and 2.4 m transitions, which agrees with them.

Calibration decided by Lance: 18 m per unit, 8 m taken as the half pipe coping-to-coping width (0.444 units). Written in docs/thps-warehouse.md as single-anchor, low confidence.

Committed as 3d5727c. task check passes (339 tests). AC #6 is a stop condition that was not triggered (the PS1 files parsed), so it is left unchecked rather than ticked.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Extracts the THPS1 Warehouse from the owner's USA PS1 disc image and records what the data says.

What changed
- scripts/thps1_extract.py reads the raw MODE2/2352 disc (ISO9660 root, CD.HED index, CD.WAD archive), cuts out skware.psx, skware_l.psx and skware_t.trg, runs a copy of the MIT thps2-tools converters, and writes .tools/thps1/warehouse/: warehouse.obj with 0..1 UVs, one warehouse.mtl, 99 texture PNGs and warehouse_nodes.json.
- Textures live in skware_l.psx. convert-psx.py desyncs on the first odd-height texture because THPS1 aligns only the width, so the script patches aligned_height to the true height in a copy.
- warehouse_nodes.json lists 5 box piles, 5 letters, the tape and 6 bonus pickups. The box piles are the five Baddy nodes with a goal counter script; the 45 Crate nodes are breakable props. The thps1_file flag does not affect this level.
- docs/thps-warehouse.md has the rerun steps with SHA-256 pins for the converter scripts, format notes, the node table, the map cross-check and the calibration.

Results
- Pile nodes match the five red circles on the items map one to one, 16 to 34 px apart; letters fit with 5 to 32 px error. The 100/200/500 cluster is not on the map.
- Calibration: 18 m per unit (half pipe coping to coping, 0.444 units, taken as 8 m). Single anchor, low confidence; it implies a room of about 36 x 56 m, larger than the docs' earlier 20-25 m by 14-17 m. The skater and vehicle models are in a different unit from the level and cannot cross-check it.

Tests
- tests/test_thps1_extract.py (18 tests, written first); task check passes with 339 tests, no ruff findings. End-to-end run on the disc reproduced the earlier manual mesh byte for byte.

Risks and follow-ups
- UVs tile past 0..1, so consumers need repeat wrapping.
- The 18 m per unit figure should be rechecked if a second anchor appears.
- Guide pile numbers (1 to 5) are still not matched to the extracted pile nodes.
- No ripped data is tracked; tools/thps1/ and .tools/ are gitignored.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
