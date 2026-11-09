# Changelog

## 0.1.0

Initial development baseline for Megabonk Level Editor.

### Create and play

- In-game editor with terrain and object tools, asset palette, undo/redo, save/load
  and from-scratch level creation.
- Versioned JSON level format (schema v4), authored spawns, randomized
  interactables, custom music and Map Selection thumbnail/biome sidecars.
- Bramblecrown Hill starter level and optional local Warehouse authoring workflow.

### Console and development tools

- Tilde console with completion, persistent history, fuzzy search and music controls.
- CLI and MCP harness for editor input, screenshots, player/run controls and
  performance diagnostics; debug/cheat commands require development mode.
- Runtime MP3 playback and optional local asset-pack support.

### Runtime and packaging

- Current plugin targets BepInEx 6 IL2CPP and the Windows game build, including
  Proton/Linux and Wine/macOS. Native Linux mod support remains unverified.
- Runtime-only Thunderstore-format package with NLayer and its license; levels,
  game references, packs and music are not included.
- Go standalone installer and Linux, Windows and macOS packaging tools are retained
  for the legacy MelonLoader runtime, not the current BepInEx plugin.
- Developer/player guides and the megabonkmod.party showcase.

Optional proprietary-derived assets stay local; this baseline does not authorize
their redistribution or announce a public package release.
