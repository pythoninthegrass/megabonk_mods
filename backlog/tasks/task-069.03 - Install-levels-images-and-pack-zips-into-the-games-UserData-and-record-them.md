---
id: TASK-069.03
title: 'Install levels, images and pack zips into the game''s UserData and record them'
status: Done
assignee: []
created_date: '2026-11-15 05:59'
labels:
  - installer
dependencies: []
references:
  - go/internal/content/content.go
  - go/internal/plan/plan.go
  - go/internal/proton/proton.go
  - src/MegabonkLevels.Mod/level_thumbnail_sidecar.cs
  - src/MegabonkLevels.Mod/pack_prefabs.cs
parent_task_id: TASK-069
priority: high
ordinal: 239000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The files the installer downloads must land exactly where the mod's loaders look for them, and the installer must remember what it installed so `--check` and `--uninstall` can work.

**Expected layout:**
- Level: `<game>/UserData/Levels/<slug>.mblevel.json`.
- Cover and biome icon: `<slug>.png` and `<slug>.biome.png` beside the level, matching `src/MegabonkLevels.Mod/level_thumbnail_sidecar.cs`.
- Pack: `<game>/UserData/LevelPacks/<id>/` holding the bundle `<id>`, `manifest.json` and `attachments.json` (`src/MegabonkLevels.Mod/pack_prefabs.cs`).

**Code to reuse in `go/internal/content`:** `ValidateLevelFile`, `ValidatePackSource`, `IsBundleName` and the path helpers.

**Zip extraction is currently duplicated** in `go/internal/plan/plan.go` and `go/internal/proton/proton.go`, both with zip-slip protection. Move it into one shared helper.

**The install record (`content.Record`) currently tracks MelonLoader state.** Change it to track:
- the installed mod version
- the BepInEx pack version
- levels: code to filename
- packs: id to version
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A level and its optional cover and biome image are written under UserData/Levels using the slug name; missing UserData folders are created
- [x] #2 An existing level file of the same name is replaced and the replacement is reported
- [x] #3 A pack zip is installed as UserData/LevelPacks/<id>/ and rejected if its contents fail pack validation
- [x] #4 Archives with paths escaping the destination are rejected
- [x] #5 Zip extraction exists in one place and the former duplicate copies are removed
- [x] #6 The install record stores mod version, BepInEx pack version, installed levels and installed packs, and round-trips through save and load
- [x] #7 Unit tests cover each behaviour using temporary directories
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

`go/internal/content` gained `install.go` (`InstallLevel`, `InstallLevelInput`/`LevelResult`,
`InstallPackFromZip`/`PackResult`, `LevelStem`, `CoverFor`, `BiomeFor`) and `record.go`
(`Record`, `LevelRecord`, `PackRecord`, `DescribeRecord`). A level lands at
`UserData/Levels/<slug>.mblevel.json` with its cover and biome image beside it as
`<slug>.png` and `<slug>.biome.png`, whichever file names they arrived with, because
`LevelThumbnailSidecar` looks images up by the level's base name. `Replaced` reports an
existing level file that was overwritten, and sidecar images from an earlier install of that
level which this install does not carry are removed and reported in `Removed` so a re-install
cannot serve a stale cover. Missing `UserData` folders are created on the way. A pack archive
is unpacked into `UserData/LevelPacks/<id>/` only after the whole archive is proven: member
names are vetted against the pack folder (climbing out, absolute, drive letter or backslash
separators are refused), each member is read through and checked against the size and checksum
its header declares, and the unpacked directory must pass `ValidatePackSource`. A refusal
leaves no pack folder behind and leaves the previously installed one untouched.

Zip extraction now lives once in `go/internal/zipx`: `Extract` unpacks an archive into a
directory and `ExtractMember` writes one vetted member, keeping its mode and optionally
capping the copy. `proton.ExtractRuntime` and `plan.extractLoader` call it and their private
`extractAll`/`extractMember` copies, including the duplicated zip-slip checks, are gone.
`thunderstore.checkPackLayout` still inspects the loader pack's member names itself: that is
a layout assertion about which folder the members sit under, not extraction.

`content.Record` now tracks `mod_version`, `bepinex_version`, `levels` as a code-to-entry map
(filename plus cover and biome) and `packs` as an id-to-version map, under schema
`megabonk-levels-install/2`, and round-trips through `SaveRecord`/`LoadRecord`. Tests are in
`go/internal/content/install_test.go`, `record_test.go` and `go/internal/zipx/zipx_test.go`,
all against temporary directories, none touching the network.

The MelonLoader-era fields the plan still writes (`files`, `runtime`, `dll_override`) and the
loader version marker helper stay for now: they belong to the loader install, and the plan and
CLI rebuild around BepInEx in the sibling tasks. `plan.go` was kept working in place so
`task installer:test` stays green, with `BepinexVersion` now taking the manifest's pinned
loader version; the plan does not install a pack zip yet, so that path reaches the game through
this package's API rather than through the current plan.

`task check` runs the C# mod build, which in this worktree fails on about 1200 missing Unity,
BepInEx and Harmony reference errors because the gitignored `.tools/` reference assemblies are
not present; `task mod:build` reports "up to date" in the main checkout, so the failure is the
missing local toolchain rather than this change. The installer gates that cover this task were
run here and pass: `task installer:test` (gofmt, `go vet`, all package tests), plus
`go test -count=1 -race` on the touched packages. `task installer:verify-static` passes in the
main checkout, where the built binaries exist, and MyGo remains the only direct module
dependency.
