# Changelog

## [0.2.0](https://github.com/pythoninthegrass/megabonk_mods/compare/v0.1.0...v0.2.0) (2026-11-09)


### Features

* **ci:** add path-filtered Thunderstore build and approved publish workflow ([63bc8a0](https://github.com/pythoninthegrass/megabonk_mods/commit/63bc8a0de98f2ad3f11eee4c07c45979ddd64072))
* **mcp:** package the harness as an installable megabonk-mcp command ([7191421](https://github.com/pythoninthegrass/megabonk_mods/commit/71914210b781b914e527f35d632c37c9c6c8ca75))
* **mcp:** register the server through uvx ([266bfab](https://github.com/pythoninthegrass/megabonk_mods/commit/266bfab2278df80b73b0aa0f13a0c8b7eae247fb))
* **site:** add searchable player wiki ([b3a5c5f](https://github.com/pythoninthegrass/megabonk_mods/commit/b3a5c5f85527138e76af5ac757a09f5de43550ab))
* **site:** link docs from showcase navigation ([cd0413f](https://github.com/pythoninthegrass/megabonk_mods/commit/cd0413fb3cbd7bbfe64a668007fc16dd1711e257))
* **thps:** add grind rails to the east deck ledge ([33ff224](https://github.com/pythoninthegrass/megabonk_mods/commit/33ff224a88a0eeaa4f18242982e328df0ca730db))
* **wine:** automate BepInEx runtime repair after r2modmac apply ([22ede08](https://github.com/pythoninthegrass/megabonk_mods/commit/22ede080775ef8fe42663260ff0c6d06bb99d07d))


### Bug Fixes

* **ci:** run Thunderstore gate tooling from the workflow commit ([12a3773](https://github.com/pythoninthegrass/megabonk_mods/commit/12a37734ef634beaa6a49e34db321a2b81b85233))
* **site:** link setup to wiki guide and public release ([2538f19](https://github.com/pythoninthegrass/megabonk_mods/commit/2538f1925681f17d68bcb1c2239f81574838720e))
* **site:** use home slug for wiki landing page ([f513448](https://github.com/pythoninthegrass/megabonk_mods/commit/f513448354b6dabb161f7358aeb9ec8257b239f6))
* **wine:** distinguish unchanged installs from completed repairs ([1f0fdad](https://github.com/pythoninthegrass/megabonk_mods/commit/1f0fdad4fdd235bd0b05959dc8c681bc05af82fe))
* **wine:** log repair details and keep success output quiet ([682c8c6](https://github.com/pythoninthegrass/megabonk_mods/commit/682c8c6014f91f49aaecdea0ff037df25c1855cb))

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
