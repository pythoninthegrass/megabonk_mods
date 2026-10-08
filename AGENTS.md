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

The mod has a development harness that loads a level, captures the game's rendered frame, and quits, without keyboard or mouse input. Enable it once with `uv run scripts/run.py enable`, launch the game, then run `uv run scripts/run.py cycle <level> <out.png>` and read the PNG. See `docs/development.md` for the commands, launch steps, and caveats.

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
