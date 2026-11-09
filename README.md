# Megabonk Level Editor

An unofficial [Megabonk](https://store.steampowered.com/app/3405340/Megabonk/)
mod for creating and playtesting custom levels: an **in-game editor**, a
**console**, and a **development harness with MCP tools**.

[Showcase](https://megabonkmod.party) · [Player guide](docs/player-guide.md) · [Build setup](docs/modding-setup.md)

> [!NOTE]
> This codebase extensively uses AI-assisted tooling (e.g., Claude Code, OpenCode, vLLM, etc.)
> 
> If that bothers you, please feel free to bounce off the repo. I wish you the best in your endeavors!
>
> For those who stick around, I *assure* you that there's a lot of care and attention with (at the time of writing) over 2780 C#, 1280 python, and dozens of less important regression tests. This is a highly methodical, spec-driven repo that is older than its git history.

## Develop

Use your own Steam copy of the **Windows game build**, natively on Windows or
through Proton/Linux or Wine/macOS. Install **BepInEx 6 IL2CPP** and launch once
to generate local interop assemblies. Native Linux mod support is unverified.
Install the toolchain in [modding setup](docs/modding-setup.md) and
[development](docs/development.md), then:

```sh
cp .env.example .env                 # configure your local game paths
uv sync
task mod:build                       # builds and deploys into your game install
task game:run
```

Press **F8** to edit/play; **backquote/tilde** opens the console (`help`, Tab
completion, Ctrl-R history). Enable `MEGABONK_DEV=true` in your local `.env` for
debug commands and automated starts. After rebuilding, restart to load the new DLL:

```sh
uv run scripts/run.py relaunch levels/bramblecrown-hill.mblevel.json
```

| Command | Purpose |
| --- | --- |
| `task check` | Build, installer tests, .NET/Python tests and lint |
| `task scripts:test` | Python tests without a running game |
| `task mod:test` | Unity-free .NET tests |
| `uv run --script scripts/mcp_server.py` | Development MCP server |
| `task package:thunderstore` | Runtime-only BepInEx package; no levels or packs |

## Explore

- [`src/`](src/) / [`tests/`](tests/) — C# plugin, pure logic and regression tests.
- [`scripts/`](scripts/) — launch, harness, MCP, level generators and packaging.
- [`levels/`](levels/) — Bramblecrown Hill, Warehouse placement data and Forest example.
- [`unity/`](unity/) — optional local asset-pack authoring.
- [`pkg/`](pkg/README.md) / [`go/`](go/) — package metadata and legacy standalone installer.
- [`site/`](site/README.md) — the showcase website.

See [level format](docs/level-format.md), [development and console commands](docs/development.md),
[asset packs](docs/asset-bundles.md), and [Thunderstore packaging](docs/thunderstore.md).

## Content and licensing

Bring your own legally obtained games and assets. Game binaries, interop assemblies,
ROMs, extracted meshes/textures and soundtrack files are not included in this
source tree. The optional Warehouse workflow extracts from your own **PS1 THPS1
USA disc image**, not a Steam release; its input checksum and local-only workflow
are documented in [Warehouse sources](docs/thps-warehouse.md#local-only-assets).
Owning a copy does not grant redistribution rights for its content or generated packs.
Retained screenshots depict gameplay; third-party rights remain with their owners.

Original project code is [Unlicense](LICENSE); third-party components retain their
own licenses. This project is not affiliated with or endorsed by Megabonk's
creators, Activision, or the Tony Hawk's Pro Skater rights holders.
