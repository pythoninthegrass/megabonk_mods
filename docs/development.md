# Development harness

The mod ships a development-only command channel so a shell script can run a load-and-check cycle against the running game without simulating keyboard or mouse input: load a level, capture the game's own rendered frame, and quit. It is driven by `scripts/run.py`.

## Enabling

The harness is off by default. It runs only if the marker file `<game dir>/harness/enabled` exists when the game starts, so a normal install exposes no command channel.

```sh
uv run scripts/run.py enable    # creates harness/enabled and harness/commands
uv run scripts/run.py disable   # removes the marker
```

Enabling takes effect on the next game launch. When active, the mod logs `DevHarness: enabled, watching '<dir>'` to `MelonLoader/Latest.log`.

The game directory is resolved the same way as in `scripts/game_paths.py`: process environment, then the nearest `.env` found walking up from the current directory or the script, then the built-in default. The keys are `MEGABONK_GAME_DIR` and `MEGABONK_BOTTLE`.

## Commands

`run.py` writes one JSON file per command into `<game dir>/harness/commands/`. The mod polls that folder twice a second, runs the files in name order, and moves each one to `harness/done/` (accepted) or `harness/rejected/` (unparseable). A command is moved before it runs, so a command that crashes or quits the game is never replayed.

| Command | Wire format | `run.py` |
| --- | --- | --- |
| Load a level and start the run | `{"command":"load-level","path":"<file>"}` | `run.py load <level>` |
| Save the rendered frame as a PNG | `{"command":"screenshot","path":"<file>"}` | `run.py screenshot <out.png>` |
| Quit the game | `{"command":"quit"}` | `run.py quit` |

`run.py cycle <level> <out.png>` runs load, waits `--settle` seconds (default 5), takes the screenshot, then quits. `--timeout` (before the subcommand) sets how long to wait for each command and for the PNG to appear. The exit code is 0 only if every step succeeded.

An unknown command, malformed JSON, or a missing or empty `path` logs `DevHarness: rejected '<file>': <reason>` and moves the file to `rejected/` without touching game state. A command that parses but fails while running logs an error and the game keeps running.

The paths in `load-level` and `screenshot` are interpreted by the game process, so `run.py` converts them (see below).

## Launching under CrossOver

Starting the game with `task game:run` opens the CrossOver Steam client, which in testing did not always go on to launch Megabonk. The harness cycle was verified by launching the executable directly in the Steam bottle while the Steam client is running:

```sh
cd "<game dir>"
SteamAppId=3405340 SteamGameId=3405340 \
  /Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin/wine --bottle Steam --cx-app Megabonk.exe
```

Caveats:

- `load-level` needs Steamworks, because the loader reads the app build id. A direct launch without `SteamAppId` fails with `Steamworks is not initialized`.
- The game sees the host filesystem as the `Z:` drive. `run.py` rewrites host paths to `Z:\...` on macOS, so pass ordinary host paths.
- `ScreenCapture.CaptureScreenshot(path)` and `ImageConversion.EncodeToPNG` both fail inside Il2CppInterop in this game build, and `ScreenCapture.CaptureScreenshotAsTexture` is unusable for the same reason. The harness reads the finished frame with `Texture2D.ReadPixels` at the end of the frame and encodes the PNG itself (`png_encoder.cs`).
- The screenshot is the game's own frame at the game's render resolution, not a capture of the host screen.
- Localhost networking was not tested; the file-drop channel needs only `System.IO`.

## Not covered

The harness does not make the player invulnerable, skip the level-up dialog, move the player or camera, or press menu buttons. An idle player can die or be blocked by the level-up dialog, so keep the settle time short.

## Character selection

A level started through the mod (`LevelLoaderPatch.LoadAndStart`, used by F6 and `load-level`) spawns Tony McZoom. The loader assigns the static `CharacterMenu.selectedCharacter` (ECharacter 13) just before `MapController.StartNewMap`; the player spawn reads that static, so no `RunConfig` field is involved. `Preferences.selectedCharacter` is the saved setting and is never written: after a mod-loaded run `Saves/LocalDir/config.json` still holds the player's own choice.

If the assignment throws, `CharacterOverride.TryApply` returns a warning that the loader logs, and the run starts with the character the menu last selected. The id lives in `character_override.cs` and mirrors `ECharacter.TonyMcZoom` in the il2cpp dump.

To confirm which character spawned, run `run.py cycle` and read the screenshot; the saved character in `config.json` differs from the one on screen when the override works.
