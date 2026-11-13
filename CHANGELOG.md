# Changelog

## [0.3.0](https://github.com/pythoninthegrass/megabonk_mods/compare/v0.2.0...v0.3.0) (2026-11-13)


### Features

* **characters:** add the Squeaker model, rig, cookie and icon ([a1fcb58](https://github.com/pythoninthegrass/megabonk_mods/commit/a1fcb58535fbf39a36a92634865f13d6617f4cf3))
* **characters:** build the squeaker asset bundle from the Squeaker FBX exports ([00f71fe](https://github.com/pythoninthegrass/megabonk_mods/commit/00f71fe12929cf6f255b47e02bf7a554c1cdbd63))
* **characters:** keep mod character runs off the Steam leaderboards ([57515da](https://github.com/pythoninthegrass/megabonk_mods/commit/57515da61f87744b86c889dfbe8ef286edf6023e))
* **characters:** register Squeaker with the Tiny Target passive and a stale cookie weapon ([a7ecf46](https://github.com/pythoninthegrass/megabonk_mods/commit/a7ecf46e3b11dbc1c033f44ecead4616bbfcf7ff))
* **characters:** wire the Squeaker controller to the player renderer's Animator parameters ([d0643ef](https://github.com/pythoninthegrass/megabonk_mods/commit/d0643ef2860e43a1228b241ba3bf60f22b4a6f15))
* **deploy:** deploy the PocketBase API with the site ([b2d0c11](https://github.com/pythoninthegrass/megabonk_mods/commit/b2d0c11db94fbee7d0f68b614a96a86366b4d4ad))
* **mcp:** add the blender MCP server ([86c65b0](https://github.com/pythoninthegrass/megabonk_mods/commit/86c65b0e34ea11516f31e0b8a02613acc9a386fe))
* **pocketbase:** add security headers to API responses ([b132af5](https://github.com/pythoninthegrass/megabonk_mods/commit/b132af581f3b5a522e793ea73bd9a342b1316257))
* **pocketbase:** add site owners and per-user level visibility ([89d4bd5](https://github.com/pythoninthegrass/megabonk_mods/commit/89d4bd53de2a4e2a85021da5af39a37c5033a7e1))
* **pocketbase:** add the level gallery API service ([dec68fb](https://github.com/pythoninthegrass/megabonk_mods/commit/dec68fbb4c92f52aee5a16022458746338877e08))
* **pocketbase:** host asset packs and categorize reports ([5c145eb](https://github.com/pythoninthegrass/megabonk_mods/commit/5c145eb119bb16d9dde0f3cbf9cfb5c41fb8507d))
* **pocketbase:** rate limit requests from the environment ([08a5e44](https://github.com/pythoninthegrass/megabonk_mods/commit/08a5e44bbd114f62d6b693c537194ef74dceaf62))
* **pocketbase:** schedule backups from environment ([f9b6655](https://github.com/pythoninthegrass/megabonk_mods/commit/f9b66553d24c7368650d9b1e5fd7c27e6f05ac8e))
* **site:** add a branded not-found page ([8e98ba6](https://github.com/pythoninthegrass/megabonk_mods/commit/8e98ba66e90b9c34e88759b9c4bc65b7e449803c))
* **site:** add a dev panel to switch users and delete levels in site:dev ([298e60e](https://github.com/pythoninthegrass/megabonk_mods/commit/298e60e4bc9841146e9b74a81871389c5860ea1e))
* **site:** add creator pages listing a maker's levels ([696d9a5](https://github.com/pythoninthegrass/megabonk_mods/commit/696d9a500444d0d32e5d650b994808bd11dd727b))
* **site:** add level gallery browse, level and upload pages ([13082f7](https://github.com/pythoninthegrass/megabonk_mods/commit/13082f7294ec4d744d75e69e28c474b6df74f313))
* **site:** add level share-code helpers and the /l/&lt;code&gt; route ([7c62b4a](https://github.com/pythoninthegrass/megabonk_mods/commit/7c62b4a3848a5067885c986e6404bff872ef75bf))
* **site:** add owner moderation controls to level cards and pages ([171aff2](https://github.com/pythoninthegrass/megabonk_mods/commit/171aff260c88dab892b05744201462f1e029374e))
* **site:** add pack pages, pack upload and copyright reports ([c5b78a0](https://github.com/pythoninthegrass/megabonk_mods/commit/c5b78a03ff87f2a0cf1ebcb1c2a0d1981df17317))
* **site:** keep the gallery stable while navigating from the showcase ([f32fc73](https://github.com/pythoninthegrass/megabonk_mods/commit/f32fc73e92645f8d670bccc101c191170c9118ff))
* **site:** like and download from the level cards ([fa17292](https://github.com/pythoninthegrass/megabonk_mods/commit/fa1729210db8e9d2025a4144ea5c295b7e8bace7))
* **site:** like and download from the level page counts ([76612d7](https://github.com/pythoninthegrass/megabonk_mods/commit/76612d740dd1c1b3e7d30d65ce48a79a4ead2a8d))
* **site:** link level owners to the edit form ([3f72b1e](https://github.com/pythoninthegrass/megabonk_mods/commit/3f72b1efb281882566b69d83977f62a43e7a4898))
* **site:** match giscus discussion titles strictly ([ca52588](https://github.com/pythoninthegrass/megabonk_mods/commit/ca525881a3eef9183625ea2cb9f0a5efb79b6901))
* **site:** offer only the sign-in providers the API has configured ([8736acc](https://github.com/pythoninthegrass/megabonk_mods/commit/8736accb2fe2869b638920edd795b4b3908bfcb9))
* **site:** open a level for editing from a link ([7ca643a](https://github.com/pythoninthegrass/megabonk_mods/commit/7ca643a607518592486d1816c34860f9ab232744))
* **site:** publish security.txt ([f089fe3](https://github.com/pythoninthegrass/megabonk_mods/commit/f089fe360c5a17866929513e4e7e877913addc18))
* **site:** revalidate html pages and send ETags ([6b6b093](https://github.com/pythoninthegrass/megabonk_mods/commit/6b6b093089b5f4835f9541681ce75af9321cbc08))
* **site:** run Mailpit and enable SMTP in the dev API ([f85e1bf](https://github.com/pythoninthegrass/megabonk_mods/commit/f85e1bf1b4dada6e650fe78461fcc2236025de8a))
* **site:** send security headers and a content security policy ([c601268](https://github.com/pythoninthegrass/megabonk_mods/commit/c601268a56959996aadd96a9af0ac3bcbd1f4ab8))
* **site:** serve wiki guides at the docs hostname root ([41d5454](https://github.com/pythoninthegrass/megabonk_mods/commit/41d5454692f189b6561c815206f718e3474d302b))
* **site:** show heart and download icons beside the counts ([e708907](https://github.com/pythoninthegrass/megabonk_mods/commit/e708907119fa5d50ee04cd83f183a3cbaac4b1ed))
* **site:** sign in as a seeded maker through a dev-only route ([33c6c68](https://github.com/pythoninthegrass/megabonk_mods/commit/33c6c684523aaa21633e93977b0b727a3f671464))
* **site:** start a seeded local API and share-link rewrites in site:dev ([d38fbe0](https://github.com/pythoninthegrass/megabonk_mods/commit/d38fbe08e6e14e692be979d463e97476e5f3e7bd))


### Bug Fixes

* **characters:** enable the Unity animation module so the squeaker bundle keeps its Animator ([fe31b0e](https://github.com/pythoninthegrass/megabonk_mods/commit/fe31b0e31f160898b2a28dd865af9abaad0dad5d))
* **characters:** keep Squeaker out of stats and tier completion saves ([d095697](https://github.com/pythoninthegrass/megabonk_mods/commit/d095697ea2bbe6b2eb2ce6f0a1ba6b42d41dc12d))
* **pocketbase:** accept a multipart update without a level file ([a545f43](https://github.com/pythoninthegrass/megabonk_mods/commit/a545f4342c336a90646d3b3cddfb161b2ab6d385))
* **pocketbase:** reject queries that probe the visibility lists ([ccd6c99](https://github.com/pythoninthegrass/megabonk_mods/commit/ccd6c99c7e7cf46e42d68f33a4214317d8e118b6))
* **site:** allow giscus stylesheet in the content security policy ([3baf4b5](https://github.com/pythoninthegrass/megabonk_mods/commit/3baf4b5bf7c45a0ec69e58c70f22373f3ad43a8f))
* **site:** clarify edit mode and tighten the mobile gallery layout ([f5b7f0f](https://github.com/pythoninthegrass/megabonk_mods/commit/f5b7f0f7e7f474d0cc815f5681e027cbbc75c136))
* **site:** disable new-login alerts on the dev API ([659ab83](https://github.com/pythoninthegrass/megabonk_mods/commit/659ab83dbd3f24eefb16b116e78b73f9f49118b5))
* **site:** rank level page actions and keep keyboard focus on delete ([15bd27f](https://github.com/pythoninthegrass/megabonk_mods/commit/15bd27f864f3daa7b2c978c0ab17687c802cd07a))
* **site:** return to the level page when canceling an edit opened from it ([400a511](https://github.com/pythoninthegrass/megabonk_mods/commit/400a5115b9bc8e3f6205aafc03c3cffc3422d019))
* **site:** shorten the dev sign-in snippet to the session fields the pages read ([1fe8f11](https://github.com/pythoninthegrass/megabonk_mods/commit/1fe8f11f242e38818da0f1a9be8944ad081fafd2))
* **site:** space and center the level page byline counts ([808bf46](https://github.com/pythoninthegrass/megabonk_mods/commit/808bf4662e5c8bd18af9308e6bace6c969ac455f))
* **site:** stop the dev API writing PocketBase migrations into the repository ([7604a2f](https://github.com/pythoninthegrass/megabonk_mods/commit/7604a2f1a6845962011842edac2886e8f9402ea0))
* **site:** stretch the share code button and pin the footer ([03a41ac](https://github.com/pythoninthegrass/megabonk_mods/commit/03a41aceee6145390d8dd587c876e085a374d7cb))
* **site:** use outline sign-in buttons on the upload page ([096d5b4](https://github.com/pythoninthegrass/megabonk_mods/commit/096d5b41e55aea0a19057c8bf646976e3e560ce6))
* **thps:** install level thumbnail and biome sidecars ([24fb152](https://github.com/pythoninthegrass/megabonk_mods/commit/24fb1524368cad7df8def8bdbf179e919dfb596f))

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
