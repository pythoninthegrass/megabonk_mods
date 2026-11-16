#!/usr/bin/env python3
"""Install or restore the offline Steamworks stub (steam_api64.dll).

The stub lets Megabonk launch without a logged-in Steam session. It is a
drop-in replacement for the game's bundled steam_api64.dll shim, so it is
fully reversible: the original is backed up on install and restored on
`restore`.

Usage:
    scripts/swap_steam_stub.py status      # report active vs stub, and backup
    scripts/swap_steam_stub.py install     # back up the real shim, drop in the stub
    scripts/swap_steam_stub.py restore     # put the backed-up original back

`status` and `restore` work without the built stub, because the stub is
recognized by a marker compiled into it; only `install` needs the artifact
from `task steamstub:build` (which needs mingw-w64). The game dir comes from
scripts/game_paths.py. The game must be quit before install/restore (a loaded
DLL cannot be overwritten).
"""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STUB = REPO / "tools" / "steamstub" / "steam_api64.dll"
# Compiled into the stub by tools/steamstub/steamstub.c, so the stub is recognizable
# without the built artifact; Valve's shim never carries it.
STUB_MARKER = b"MEGABONK_STEAM_FAIL_INIT"
ACTIONS = ("status", "install", "restore")


def game_dir() -> Path:
    out = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "game_paths.py")],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return Path(json.loads(out)["game_dir"])


def shim_path(game: Path) -> Path:
    return game / "Megabonk_Data" / "Plugins" / "x86_64" / "steam_api64.dll"


def backup_path(shim: Path) -> Path:
    return shim.with_name(shim.name + ".steamstub.bak")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def active_state(shim: Path, bak: Path) -> str:
    if not shim.exists():
        return "MISSING"
    data = shim.read_bytes()
    if STUB_MARKER in data or (STUB.exists() and data == STUB.read_bytes()):
        return "STUB"
    if bak.exists() and data == bak.read_bytes():
        return "ORIGINAL"
    return "UNKNOWN"


def describe(p: Path, missing: str = "<absent>") -> str:
    return f"{p}  ({sha256(p)})" if p.exists() else f"{p}  {missing}"


def do_status(game: Path, shim: Path, bak: Path) -> int:
    print(f"game dir : {game}")
    print(f"shim     : {describe(shim)}")
    print(f"stub     : {describe(STUB, '<not built: task steamstub:build>')}")
    print(f"backup   : {describe(bak, '<missing>')}")
    print(f"active   : {active_state(shim, bak)}")
    return 0


def do_install(shim: Path, bak: Path) -> int:
    if not STUB.exists():
        print(f"stub not found: {STUB} (build it: task steamstub:build)")
        return 1
    if not shim.exists():
        print(f"shim not found: {shim}; nothing to back up (run restore if a backup exists)")
        return 1
    state = active_state(shim, bak)
    if state == "STUB" and not bak.exists():
        print(f"the shim is already the stub and {bak.name} is missing; refusing to record the stub as the original")
        return 1
    if not bak.exists():
        shutil.copy2(shim, bak)
        print(f"backed up original -> {bak.name}")
    if state == "STUB" and sha256(shim) == sha256(STUB):
        print(f"stub already installed ({sha256(shim)}) from {STUB}")
        return 0
    shutil.copy2(STUB, shim)
    print(f"installed STUB -> {shim}  ({sha256(shim)})  from {STUB}")
    print("relaunch the game to load it; quit first (a loaded DLL can't be overwritten).")
    return 0


def do_restore(shim: Path, bak: Path) -> int:
    if not bak.exists():
        print(f"no backup at {bak.name}; nothing to restore")
        return 1
    shim.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(bak, shim)
    print(f"restored ORIGINAL -> {shim.name}  ({sha256(shim)})")
    return 0


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ACTIONS:
        print(__doc__)
        return 2

    action = sys.argv[1]
    try:
        game = game_dir()
    except (subprocess.CalledProcessError, OSError, ValueError, KeyError) as exc:
        detail = exc.stderr.strip().splitlines()[-1] if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else exc
        print(f"cannot resolve the game dir: {detail}")
        print("set MEGABONK_GAME_DIR, or MEGABONK_WINE_PREFIX, in the environment or .env")
        return 1

    shim = shim_path(game)
    bak = backup_path(shim)
    if action == "status":
        return do_status(game, shim, bak)
    if action == "install":
        return do_install(shim, bak)
    return do_restore(shim, bak)


if __name__ == "__main__":
    raise SystemExit(main())
