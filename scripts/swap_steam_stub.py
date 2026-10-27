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

The stub is built by tools/steamstub/build.sh (needs mingw-w64). The game dir
comes from scripts/game_paths.py. The game must be quit before install/restore
(a loaded DLL cannot be overwritten).
"""
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STUB = REPO / "tools" / "steamstub" / "steam_api64.dll"
BACKUP = None  # set below from game dir


def game_dir() -> Path:
    out = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "game_paths.py")],
        check=True, capture_output=True, text=True,
    ).stdout
    import json
    return Path(json.loads(out)["game_dir"])


def shim_path(game: Path) -> Path:
    return game / "Megabonk_Data" / "Plugins" / "x86_64" / "steam_api64.dll"


def backup_path(shim: Path) -> Path:
    return shim.with_name(shim.name + ".steamstub.bak")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def active_is_stub(shim: Path) -> bool:
    return STUB.exists() and sha256(shim) == sha256(STUB)


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ("status", "install", "restore"):
        print(__doc__)
        return 2

    action = sys.argv[1]
    if not STUB.exists():
        print(f"stub not found: {STUB} (build it: bash tools/steamstub/build.sh)")
        return 1
    game = game_dir()
    shim = shim_path(game)
    bak = backup_path(shim)

    if not shim.exists():
        print(f"shim not found: {shim}")
        return 1

    if action == "status":
        print(f"game dir : {game}")
        print(f"shim     : {shim}  ({sha256(shim)})")
        print(f"stub     : {STUB}  ({sha256(STUB)})")
        print(f"backup   : {bak if bak.exists() else '<missing>'}")
        print(f"active   : {'STUB' if active_is_stub(shim) else 'ORIGINAL'}")
        return 0

    if action == "install":
        if not bak.exists():
            shutil.copy2(shim, bak)
            print(f"backed up original -> {bak.name}")
        shutil.copy2(STUB, shim)
        print(f"installed STUB -> {shim.name}  ({sha256(shim)})")
        print("relaunch the game to load it; quit first (a loaded DLL can't be overwritten).")
        return 0

    if action == "restore":
        if not bak.exists():
            print(f"no backup at {bak.name}; nothing to restore")
            return 1
        shutil.copy2(bak, shim)
        print(f"restored ORIGINAL -> {shim.name}  ({sha256(shim)})")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
