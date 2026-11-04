# AGENTS.md

This file provides guidance to AI agents when working with code in this repository.

## Quickstart

- Launch the Warehouse level as Tony McZoom in editor mode: `task game:editor -- levels/thps.mblevel.json`. It needs `MEGABONK_DEV=true` in `.env` and the `thps` pack installed in the game; run `task mod:build` first after a code change. `levels/thps-editable.mblevel.json` is the piece-assembled editable variant. See [Loading the THPS level](#loading-the-thps-level).

## Linux and Flatpak Steam caveats

Megabonk ships a native Linux build (`Megabonk.x86_64`); when running that build there is no Proton or Wine prefix and the CrossOver `version.dll` override does not apply. `compatdata/3405340` can stay empty. The caveats below concern that native-build setup, not the Windows build under Proton.

For the Windows build under Proton, see [Gamepadui and remote Steam hosts](docs/gamepadui.md) for prefix detection, installation, launch/quit and content transfer.

- MelonLoader loads through `LD_PRELOAD`, set in the game's Steam launch options. Reference the library by filename only and add the game directory to `LD_LIBRARY_PATH`: `DOTNET_ROOT="<dotnet6>" LD_LIBRARY_PATH="<game dir>:$LD_LIBRARY_PATH" LD_PRELOAD="MelonLoader.Bootstrap.so:$LD_PRELOAD" %command%`.
- Il2Cpp MelonLoader needs a .NET 6 runtime. A newer runtime on the host (the repo's mise toolchain provides .NET 10) is not enough. Install 6.0 with `dotnet-install.sh --runtime dotnet --channel 6.0 --install-dir <dir> --no-path` and point `DOTNET_ROOT` at it.
- Flatpak Steam only sees the paths granted to it (`flatpak override --show com.valvesoftware.Steam`). Put the .NET 6 install under a granted path such as the Steam library root, not under `$HOME` or a mise directory.
- Steam rewrites `userdata/<id>/config/localconfig.vdf` while it runs. To set launch options without the UI, shut Steam down first (`flatpak run com.valvesoftware.Steam -shutdown`), edit `LaunchOptions` under the app id (3405340), then start Steam again. Keep a backup of the file.
- Starting Steam from a non-graphical shell fails with "Unable to open X11 display" under KDE Wayland. Pass `DISPLAY=:0` and `XAUTHORITY` set to the `/run/user/<uid>/xauth_*` file named in the `Xwayland` command line (`pgrep -a Xwayland`).
- Do not use `pkill -f` with a pattern that also appears in the calling shell's own command line; it kills that shell. Use `pkill -x Megabonk.x86_64`.
- `task game:run` falls back to `flatpak run com.valvesoftware.Steam steam://rungameid/3405340` when no native `steam` binary exists, and defaults `DISPLAY` and `XAUTHORITY` itself.
- The first launch with MelonLoader runs the Il2Cpp assembly generator (Cpp2IL, Il2CppInterop) and takes about 30 seconds. Check `MelonLoader/Latest.log` in the game directory for `Assembly Generation Successful!` and the `Mods loaded` line.

## Gamepadui and remote Steam hosts

`docs/gamepadui.md` covers standing up a gamescope + Steam gamepadui session (distro `gamescope`, `steam-devices`, `mangohud`, and the `pvermeer/gamescope-session-guide` COPR for a GDM session or a `~/.local/share/applications` launcher: `gamescope -e -f --mangoapp -- steam -steamdeck -steamos3`; `-f` because it runs nested in GNOME) and the Proton install/verify workflow over SSH. Its "What it took" section records the details that cost real time to discover; the ones that change what to try first:

- Screenshots over SSH: GNOME's direct screenshot D-Bus API can refuse access; the desktop portal works. See [GNOME screenshots over SSH](docs/development.md#gnome-screenshots-over-ssh). The compositor is `gamescope-wl`, not `gamescope`; nested Xwayland captures can miss overlays.
- Under a gamescope session Steam **respawns when killed** and rewrites `localconfig.vdf` while alive, so a Compatibility edit made against a live client is silently lost. Bring the whole session down first. `steam steam://shutdownsteam` is a no-op there; `pkill -TERM -x steam` works.
- `compat_log.txt` can log `Mapping AppID 3405340 to tool "native" with priority 85` even with correct `CompatToolMapping` and `Apps/3405340/compat` keys. `appmanifest_3405340.acf` depot ids are the ground truth for which build is installed: 3405341 is Linux, 3405342 Windows. Selecting Proton in the GUI triggers the depot update; hand-writing the mapping alone did not. Select the recommended DX11 launch option, pin `-force-d3d11`, and confirm Direct3D 11 in the active prefix's `Player.log`.
- Where `uv` comes from mise it is absent from the non-interactive SSH PATH: invoke with `mise exec -- uv run ...` and give `menu --remote-python` an **absolute** venv interpreter path (`~/…` is passed unexpanded).

## Verifying changes in the running game

The mod has a development harness that loads a level, captures the game's rendered frame, drives the editor with injected key, mouse and text input, teleports the player, and quits, without OS-level input. Prefer it through the MCP server named `megabonk` (`scripts/mcp_server.py`): an agent calls typed tools (`relaunch`, `load`, `screenshot`, `state`, `key`, `mouse`, `type_text`, `teleport`, `dismiss_levelup`, and the rest) and gets screenshots back inline. See the "MCP server" section and its "End-to-end check" walkthrough in `docs/development.md`.

The fallback is the same harness through `scripts/run.py`. Enable it once with `uv run scripts/run.py enable`, launch the game, then run `uv run scripts/run.py cycle <level> <out.png>` (or `relaunch`, below) and read the PNG. See `docs/development.md` for the commands, launch steps, and caveats.

Stock Rewired menus/gamepadui need OS-level input, not the harness's editor `key`/`mouse` injection. Use `scripts/run.py menu start|status|drive|stop` (Linux uinput and X11), with `--host` and `--remote-repo` for SSH targets. The maintained batch driver supports real keyboard/controller/mouse input, read-only harness diagnostics and downloading screenshots. Start devices before the game when possible and always stop them afterward. See [Driving stock menus with run.py](docs/gamepadui.md#driving-stock-menus-with-runpy) for dependencies, permissions, display selection and examples; do not recreate the scratch wm2 input scripts. `drive` takes the JSON batch as a positional argument with `--settle` seconds between actions (no `--batch` flag, no `[ms]` delay element), and keyboard input must name the whitelisted constants (`["key","KEY_DOWN"]`) — `menu` has no `key`/`mouse`/`type` verbs, and the top-level `run.py` commands of those names post to the editor harness, which ignores them outside editor mode while still reporting success.

### Reloading a rebuilt mod

MelonLoader loads the DLL once at startup, so a rebuild only takes effect on a fresh launch. Run `task mod:build` (it deploys the DLL into `Mods`), then run `uv run scripts/run.py relaunch` to quit the old game, launch a fresh instance, load `levels/example-forest.mblevel.json`, and enter editor mode. `relaunch` waits for a new harness log entry, retries the load until the kill floor arms, then enables editor mode. The player gets 2 Feathers (`MEGABONK_RELAUNCH_FEATHERS`, 0 leaves them alone), enemy spawns stay on and the player takes normal damage by default; set `MEGABONK_RELAUNCH_SPAWNS=false` to stop spawns and `MEGABONK_RELAUNCH_INVULNERABLE=true` to make the player invulnerable (in the environment or `.env`; `task` loads `.env` through its `dotenv` directive). The MCP `spawns` and `invulnerable` tools and `run.py spawns` and `run.py invulnerable` change either at runtime (see "Enemy spawns" in `docs/development.md`). A level `load` into a running game turns spawns back on, so send `spawns off` again after it. Pass an optional level path to test a different file. Set `MEGABONK_DEV=true` in `.env` first: without it a `load` waits for a character to be confirmed on the game's Character Selection screen and the kill floor never arms; with it the run starts as Tony McZoom, or as the character named by `--character calcium`. The manual sequence remains useful when diagnosing a failed relaunch:

```sh
L="$(uv run scripts/game_paths.py | jq -r .latest_log_path)"
uv run scripts/run.py quit && m="$(mktemp)" && task game:run
until [ "$L" -nt "$m" ] && rg -q 'DevHarness: enabled' "$L"; do sleep 2; done
for i in 1 2 3 4 5; do
  uv run scripts/run.py load <level>
  for j in $(seq 1 10); do rg -q 'KillFloor: armed' "$L" && break; sleep 1; done
  rg -q 'KillFloor: armed' "$L" && break
done
uv run scripts/run.py editor on
```

`task game:run` returns at once because it detaches the game. Send the load only until it succeeds; a second `load` restarts the run. `<level>` is a level file, such as `levels/example-forest.mblevel.json`, not a stage name. Once the kill floor arms, send `editor on` straight away, so the game opens in the map editor (frozen run, free-fly camera) ready to test; confirm `EditorMode: entered` in the log. Always relaunch rather than sending a second `load` into a running game: a reload over a run that was left unattended once left the player dead, and entering the editor late lets enemies reach an idle player. The whole chain has been run end to end on the CrossOver setup and on a copied plain-Wine prefix on a second Mac (see "Setting up a second machine" in `docs/development.md`).

### Loading the THPS level

`levels/thps.mblevel.json` is generated by `scripts/build_thps_level.py` and needs the `thps` pack installed in the game, or the Warehouse shows as a placeholder (`pack 'thps' is not installed` in the log). The pack bundle comes from gitignored `.tools/` files; see "Loading the THPS level" in `docs/development.md` for the regenerate, install and relaunch steps and for copying a built bundle between machines.

### Launching without a Steam session

Prefer the steamstub for offline development: with `tools/steamstub/`'s drop-in `steam_api64.dll` installed (`task steamstub:install`, reversible with `task steamstub:restore`), the game launches and plays with Steam stopped — no login and no signing other machines out. Launch through the same `task game:run` and `relaunch`; direct-Proton runs on Linux hosts use the same stub. See "Launching without a Steam session" in `docs/development.md`.

## Reading the game's code

Megabonk is an Il2Cpp build with no managed IL anywhere in the install. `MelonLoader/Il2CppAssemblies/*.dll` and Il2CppDumper's `DummyDll/*.dll` are both stubs — interop thunks and empty method bodies — so decompiling either returns plumbing, never game logic. Read `.tools/il2cpp_dump/dump.cs` (regenerate with `task re:dump`) for fields, method signatures and enum values; a method body exists only as native code in `GameAssembly`, reachable in Ghidra or Binary Ninja at the RVA the dump lists. Ghidra is wired into the REA MCP tools through environment variables in `.claude/settings.json`; see "Using Ghidra through REA" in `docs/development.md` for the setup and for binding it with `provider_id: "ghidra"`. Behaviour that lives in a serialized Unity asset rather than in code, such as Rewired's key bindings, is in neither place and has to be confirmed in the running game. See `docs/development.md` for the detail and the one-command check.

`.tools/` is gitignored, so `rg` skips it by default. Pass `-u` (`--no-ignore`, honours `.gitignore` off) to search gitignored files, or `-uu` to also include hidden files, e.g. `rg -u 'RandomMapObject' .tools/il2cpp_dump/dump.cs`. Prefer scoping the search to the specific path over `-uu` across the repo. `-u` also sidesteps a `rg` quirk where a malformed `.gitignore` glob (such as the `Icon[` / `.HFS+ Private Directory Data[` entries here) prints a parse error and can mangle matched-line output.

## Python tests

The Python tests are in `tests/` and run with `task scripts:test` or `uv run pytest` (append a test path for a focused run). Dependencies come from `pyproject.toml` and `uv.lock`: runtime packages under `[project.dependencies]`, test tooling under `[dependency-groups] dev`, which uv installs by default, so no `--extra` or `--with` flags are needed. `tests/conftest.py` isolates every test from `MEGABONK_*` settings and the repo `.env`. See [Python tests](docs/development.md#python-tests) for the pytest configuration, the `[tool.uv]` resolution pins and the separate PEP 723 script environment.

Two conftest rules surprise people: a `FileNotFoundError` on any path in `GENERATED_ARTIFACTS` skips the test rather than failing (so a missing gitignored build product is never a red suite, and a product that exists but is malformed still fails), and an autouse fixture replaces `os.kill` with a stub that raises, so a test that signals a process installs its own recorder.

## Honcho memory

Honcho is the persistent memory here; Serena's memory and onboarding tools are disabled. The workspace id and the two peer ids to use are listed under "Honcho" in `CLAUDE.local.md` (untracked, per-fleet). The calls that matter, in order: `create_session` (that workspace id, a unique `session_id`, `metadata` a JSON string naming the repo path), `add_peers_to_session` (the human peer with `observe_me` and `observe_others` true, the `Assistant` peer with `observe_me: false`), then `add_messages_to_session` reusing that one `session_id` for the whole conversation rather than minting one per turn.

- Redact before writing. Nothing personal goes into Honcho or into a tracked file even when it is true: names, usernames, emails, LAN or tailscale addresses, account ids, and host-specific home paths. Write the role instead ("the maintainer host", "the Linux player box", `<user>`), and put the identifier itself in `CLAUDE.local.md`.

- Confirm a write with `get_session_context`, not `search`. Derivation is asynchronous and `search` ranks across the whole workspace, so a message written seconds ago can be missing from the top hits; re-adding it on that evidence produces duplicates.
- Expect a second session holding the raw transcript, recorded automatically under an `opencode-<repo>` id. Curated durable facts belong in your own session; read both before concluding Honcho knows nothing.
- Prefer `get_session_context`, `get_peer_context`, `get_representation` and `search`, which return at once. `chat` and `workspace_chat` run live reasoning for seconds; use them when a reasoned answer actually changes what you write.
- Record decisions, rules and preferences, not command logs, source dumps, or anything from `.env`.

## Comments in code (all languages)

No section-banner or multi-paragraph comments, in `.cs`, `.py`, `.sh`, or anywhere else. Code should be self-explanatory; put design rationale in `docs/*.md` instead. A comment above a function, method, or field is at most 1-2 lines, and only when naming alone doesn't make intent clear.

## Attribution

Leave no agent, harness, model or tool watermark on anything written to the
repository. Commit messages are the conventional subject and body only: never
`Co-Authored-By`, `Generated with`, or a tool/model name. Backlog tasks keep an
empty assignee and Backlog comments carry no `author:` label — do not pass
`assignee` agent names or `commentAuthor` (the Backlog MCP stamps nothing when
they are omitted).

## Writing docs/*.md

Document the content itself — the schema, the rule, the API, the gotcha — not which task or AC introduced it. Don't cite `TASK-###` IDs, acceptance-criteria numbers, or phrasing like "per the final TASK-002.03 runtime finding"; that provenance is already tracked in Backlog and `git log`/`git blame`, and it rots as tasks close and get archived. Exception: a genuinely open, unresolved question (e.g. "this assumption is unconfirmed, revisit once real data is available") belongs in the doc as a TODO, but phrase it about the open question itself, not the task number that will close it.

## Gotchas

- BSD sed (macOS) does not expand `\n` in a replacement, so `sed -i 's/a/a\nb/'` fails with "unterminated substitute pattern". Use a Python one-liner, or the Edit tool, for multi-line replacements.

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
