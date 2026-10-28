# AGENTS.md

This file provides guidance to AI agents when working with code in this repository.

## Linux and Flatpak Steam caveats

Megabonk ships a native Linux build (`Megabonk.x86_64`), so there is no Proton or Wine prefix and the CrossOver `version.dll` override does not apply. `compatdata/3405340` stays an empty directory.

- MelonLoader loads through `LD_PRELOAD`, set in the game's Steam launch options. Reference the library by filename only and add the game directory to `LD_LIBRARY_PATH`: `DOTNET_ROOT="<dotnet6>" LD_LIBRARY_PATH="<game dir>:$LD_LIBRARY_PATH" LD_PRELOAD="MelonLoader.Bootstrap.so:$LD_PRELOAD" %command%`.
- Il2Cpp MelonLoader needs a .NET 6 runtime. A newer runtime on the host (the repo's mise toolchain provides .NET 10) is not enough. Install 6.0 with `dotnet-install.sh --runtime dotnet --channel 6.0 --install-dir <dir> --no-path` and point `DOTNET_ROOT` at it.
- Flatpak Steam only sees the paths granted to it (`flatpak override --show com.valvesoftware.Steam`). Put the .NET 6 install under a granted path such as the Steam library root, not under `$HOME` or a mise directory.
- Steam rewrites `userdata/<id>/config/localconfig.vdf` while it runs. To set launch options without the UI, shut Steam down first (`flatpak run com.valvesoftware.Steam -shutdown`), edit `LaunchOptions` under the app id (3405340), then start Steam again. Keep a backup of the file.
- Starting Steam from a non-graphical shell fails with "Unable to open X11 display" under KDE Wayland. Pass `DISPLAY=:0` and `XAUTHORITY` set to the `/run/user/<uid>/xauth_*` file named in the `Xwayland` command line (`pgrep -a Xwayland`).
- Do not use `pkill -f` with a pattern that also appears in the calling shell's own command line; it kills that shell. Use `pkill -x Megabonk.x86_64`.
- `task game:run` falls back to `flatpak run com.valvesoftware.Steam steam://rungameid/3405340` when no native `steam` binary exists, and defaults `DISPLAY` and `XAUTHORITY` itself.
- The first launch with MelonLoader runs the Il2Cpp assembly generator (Cpp2IL, Il2CppInterop) and takes about 30 seconds. Check `MelonLoader/Latest.log` in the game directory for `Assembly Generation Successful!` and the `Mods loaded` line.

## Verifying changes in the running game

The mod has a development harness that loads a level, captures the game's rendered frame, drives the editor with injected key, mouse and text input, teleports the player, and quits, without OS-level input. Prefer it through the MCP server named `megabonk` (`scripts/mcp_server.py`): an agent calls typed tools (`relaunch`, `load`, `screenshot`, `state`, `key`, `mouse`, `type_text`, `teleport`, `dismiss_levelup`, and the rest) and gets screenshots back inline. See the "MCP server" section and its "End-to-end check" walkthrough in `docs/development.md`.

The fallback is the same harness through `scripts/run.py`. Enable it once with `uv run scripts/run.py enable`, launch the game, then run `uv run scripts/run.py cycle <level> <out.png>` (or `relaunch`, below) and read the PNG. See `docs/development.md` for the commands, launch steps, and caveats.

### Reloading a rebuilt mod

MelonLoader loads the DLL once at startup, so a rebuild only takes effect on a fresh launch. Run `task mod:build` (it deploys the DLL into `Mods`), then run `uv run scripts/run.py relaunch` to quit the old game, launch a fresh instance, load `levels/example-forest.mblevel.json`, and enter editor mode. `relaunch` waits for a new harness log entry, retries the load until the kill floor arms, then enables invulnerability, stops enemy spawns and enables editor mode. Spawns stay off after a relaunch by default; start them for an end-to-end run with the MCP `spawns(on=true)` or `uv run scripts/run.py spawns on`, or set `MEGABONK_RELAUNCH_SPAWNS=true` to leave them on from the start (see "Enemy spawns" in `docs/development.md`). A level `load` into a running game turns them back on, so send `spawns off` again after it. Pass an optional level path to test a different file. The manual sequence remains useful when diagnosing a failed relaunch:

```sh
L="$(uv run scripts/game_paths.py | jq -r .latest_log_path)"
uv run scripts/run.py quit && m="$(mktemp)" && task game:run
until [ "$L" -nt "$m" ] && rg -q 'DevHarness: enabled' "$L"; do sleep 2; done
for i in 1 2 3 4 5; do
  uv run scripts/run.py load <level>
  for j in $(seq 1 10); do rg -q 'KillFloor: armed' "$L" && break; sleep 1; done
  rg -q 'KillFloor: armed' "$L" && break
done
uv run scripts/run.py invulnerable && uv run scripts/run.py spawns off && uv run scripts/run.py editor on
```

`task game:run` returns at once because it detaches the game. Send the load only until it succeeds; a second `load` restarts the run. `<level>` is a level file, such as `levels/example-forest.mblevel.json`, not a stage name. Once the kill floor arms, send `invulnerable`, `spawns off` and then `editor on` straight away, so the idle player is not killed by enemies while the run waits and the game opens in the map editor (frozen run, free-fly camera) ready to test; confirm `EditorMode: entered` in the log. Always relaunch rather than sending a second `load` into a running game: a reload over a run that was left unattended once left the player dead, and entering the editor late lets enemies reach an idle player. The whole chain has been run end to end on the CrossOver setup and on a copied plain-Wine prefix on a second Mac (see "Setting up a second machine" in `docs/development.md`).

### Launching without a Steam session

Steam allows one session per account across devices, so a second Mac signing in signs the first out. For multi-machine work, `tools/steamstub/` provides a drop-in `steam_api64.dll` that lets the game launch and play with Steam stopped — no login, no `SteamAppId`/`SteamGameId`. Install it with `task steamstub:install` (reversible with `task steamstub:restore`), then launch through the same `task game:run` and `relaunch`. The game tolerates the failed `SteamAPI.Init()` and continues to the main menu, and `load-level` still works. See "Launching without a Steam session" in `docs/development.md`.

## Reading the game's code

Megabonk is an Il2Cpp build with no managed IL anywhere in the install. `MelonLoader/Il2CppAssemblies/*.dll` and Il2CppDumper's `DummyDll/*.dll` are both stubs — interop thunks and empty method bodies — so decompiling either returns plumbing, never game logic. Read `.tools/il2cpp_dump/dump.cs` (regenerate with `task re:dump`) for fields, method signatures and enum values; a method body exists only as native code in `GameAssembly`, reachable in Ghidra or Binary Ninja at the RVA the dump lists. Ghidra is wired into the REA MCP tools through environment variables in `.claude/settings.json`; see "Using Ghidra through REA" in `docs/development.md` for the setup and for binding it with `provider_id: "ghidra"`. Behaviour that lives in a serialized Unity asset rather than in code, such as Rewired's key bindings, is in neither place and has to be confirmed in the running game. See `docs/development.md` for the detail and the one-command check.

`.tools/` is gitignored, so `rg` skips it by default. Pass `-u` (`--no-ignore`, honours `.gitignore` off) to search gitignored files, or `-uu` to also include hidden files, e.g. `rg -u 'RandomMapObject' .tools/il2cpp_dump/dump.cs`. Prefer scoping the search to the specific path over `-uu` across the repo. `-u` also sidesteps a `rg` quirk where a malformed `.gitignore` glob (such as the `Icon[` / `.HFS+ Private Directory Data[` entries here) prints a parse error and can mangle matched-line output.

## Python tests

The Python tests are in `tests/` and run with `task scripts:test` (pytest). `tests/conftest.py` isolates every test from `MEGABONK_*` settings and the repo `.env`; see "Python tests" in `docs/development.md`.

## Comments in code (all languages)

No section-banner or multi-paragraph comments, in `.cs`, `.py`, `.sh`, or anywhere else. Code should be self-explanatory; put design rationale in `docs/*.md` instead. A comment above a function, method, or field is at most 1-2 lines, and only when naming alone doesn't make intent clear.

## Writing docs/*.md

Document the content itself — the schema, the rule, the API, the gotcha — not which task or AC introduced it. Don't cite `TASK-###` IDs, acceptance-criteria numbers, or phrasing like "per the final TASK-002.03 runtime finding"; that provenance is already tracked in Backlog and `git log`/`git blame`, and it rots as tasks close and get archived. Exception: a genuinely open, unresolved question (e.g. "this assumption is unconfirmed, revisit once real data is available") belongs in the doc as a TODO, but phrase it about the open question itself, not the task number that will close it.

## Context7 Libraries

- astral-sh/docs
- j178/prek
- jdx/mise
- mrlesk/backlog.md
- websites/binary_ninja
- websites/taskfile_dev

<!-- BACKLOG.MD MCP GUIDELINES START -->
<!-- backlog.md-instructions-version: 1.48.0 -->

<CRITICAL_INSTRUCTION>

## BACKLOG WORKFLOW INSTRUCTIONS

This project uses Backlog.md MCP for all task and project management activities.

**CRITICAL GUIDANCE**

- If your client supports MCP resources, read `backlog://workflow/overview` to understand when and how to use Backlog for this project.
- If your client only supports tools or the above request fails, call `backlog.get_backlog_instructions()` to load the tool-oriented overview. Use the `instruction` selector when you need `task-creation`, `task-execution`, or `task-finalization`.

- **First time working here?** Read the overview resource IMMEDIATELY to learn the workflow
- **Already familiar?** You should have the overview cached ("## Backlog.md Overview (MCP)")
- **When to read it**: BEFORE creating tasks, or when you're unsure whether to track work

These guides cover:

- Decision framework for when to create tasks
- Search-first workflow to avoid duplicates
- Links to detailed guides for task creation, execution, and finalization
- MCP tools reference

You MUST read the overview resource to understand the complete workflow. The information is NOT summarized here.

</CRITICAL_INSTRUCTION>

<!-- BACKLOG.MD MCP GUIDELINES END -->
