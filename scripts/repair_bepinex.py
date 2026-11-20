#!/usr/bin/env python3
"""Restore files omitted by r2modmac Apply without replacing manager-owned files."""

import argparse
import hashlib
import io
import os
import stat
import sys
import zipfile
from asset_download import DownloadError, MissingAsset, download
from datetime import UTC, datetime, timezone
from megabonk_harness.game_paths import game_dir
from megabonk_harness.run import game_is_running
from pathlib import Path, PurePosixPath

PACK_NAME = "BepInEx-BepInExPack_IL2CPP-6.0.788.zip"
PACK_URL = f"https://gcdn.thunderstore.io/live/repository/packages/{PACK_NAME}"
PACK_SHA256 = "ce25d925f9eaba817214f5d6b2083b8e135ed0592b5a61b9f75ea5d4c02f5300"
CACHE = Path(__file__).resolve().parents[1] / ".tools/vendor-cache" / PACK_NAME
LOG_FILE = Path(__file__).resolve().parents[1] / ".tools/logs/bepinex-repair.log"
METADATA = (".doorstop_version", "changelog.txt")
PREREQUISITES = (
    "Megabonk.exe",
    "winhttp.dll",
    "doorstop_config.ini",
    "BepInEx/core/BepInEx.Unity.IL2CPP.dll",
)
DOORSTOP_FILE = "doorstop_config.ini"
DOORSTOP_RELATIVE = {
    "target_assembly": "BepInEx\\core\\BepInEx.Unity.IL2CPP.dll",
    "dll_search_path_override": "BepInEx\\core",
    "coreclr_path": "dotnet\\coreclr.dll",
    "corlibDir": "dotnet",
}
STALE_ASSEMBLY_CACHE = "BepInEx/cache/chainloader_typeloader.dat"


def payload(body: bytes) -> dict[str, bytes]:
    if hashlib.sha256(body).hexdigest() != PACK_SHA256:
        raise ValueError("Pack checksum mismatch; expected the pinned BepInExPack IL2CPP 6.0.788 ZIP")
    files = {}
    seen = set()
    total = 0
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        for member in archive.infolist():
            prefix = "BepInExPack/"
            if not member.filename.startswith(prefix) or member.is_dir():
                continue
            name = member.filename[len(prefix) :]
            if name not in METADATA and not name.startswith("dotnet/"):
                continue
            path = PurePosixPath(name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in name
                or ":" in name
                or stat.S_ISLNK(member.external_attr >> 16)
                or name.casefold() in seen
            ):
                raise ValueError(f"Unsafe or duplicate archive member: {name}")
            total += member.file_size
            if total > 400 * 1024 * 1024:
                raise ValueError("Pack runtime exceeds the extraction size limit")
            seen.add(name.casefold())
            files[name] = archive.read(member)
    for required in (*METADATA, "dotnet/coreclr.dll"):
        if required not in files:
            raise ValueError(f"Pack is missing {required}")
    return files


def safe_target(game: Path, name: str) -> Path:
    target = game / name
    for part in (target, *target.parents):
        if part == game:
            break
        if part.is_symlink():
            raise ValueError(f"Refusing symlink destination: {part}")
        if part != target and part.exists() and not part.is_dir():
            raise ValueError(f"Destination parent is not a directory: {part}")
    return target


def require_stopped() -> None:
    if game_is_running():
        raise ValueError("Quit Megabonk before repairing BepInEx; no processes will be stopped automatically")


def _is_absolute(value: str) -> bool:
    value = value.strip()
    return value.startswith(("/", "\\")) or (len(value) > 1 and value[1] == ":")


def _ends_under(value: str, expected: str) -> bool:
    got = value.strip().replace("\\", "/").casefold()
    want = expected.replace("\\", "/").casefold()
    return got == want or got.endswith("/" + want)


def plan_doorstop(game: Path) -> tuple[list[str], bytes | None]:
    """Plan the doorstop_config.ini fix; a manager may record this install's own folder absolutely."""
    config = game / DOORSTOP_FILE
    if not config.is_file():
        return [], None
    expected = {key.casefold(): value for key, value in DOORSTOP_RELATIVE.items()}
    raw = config.read_bytes().decode("utf-8", errors="ignore")
    newline = "\r\n" if "\r\n" in raw else "\n"
    actions: list[str] = []
    lines: list[str] = []
    rewritten = False
    for line in raw.splitlines():
        key, sep, value = line.partition("=")
        target = expected.get(key.strip().casefold()) if sep else None
        if target and _is_absolute(value) and _ends_under(value, target):
            actions.append(f"doorstop {key.strip()} -> {target}")
            lines.append(f"{key}={target}")
            rewritten = True
        elif target and _is_absolute(value):
            actions.append(f"left absolute doorstop {key.strip()} ({value.strip()}); it points outside this game folder")
            lines.append(line)
        else:
            lines.append(line)
    if not rewritten:
        return actions, None
    text = newline.join(lines)
    body = (text + newline) if raw.endswith("\n") else text
    return actions, body.encode("utf-8")


def repair(game: Path, body: bytes, *, dry_run: bool = False) -> list[str]:
    require_stopped()
    game = game.expanduser().resolve()
    for name in PREREQUISITES:
        if not safe_target(game, name).is_file():
            raise ValueError(f"Missing {name}; install BepInExPack in r2modmac and Apply first")
    files = payload(body)
    missing = {}
    for name, data in files.items():
        target = safe_target(game, name)
        if target.exists():
            if not target.is_file() or target.read_bytes() != data:
                raise ValueError(f"Existing file differs from the pinned pack; refusing to overwrite: {target}")
        else:
            missing[name] = data
    doorstop_actions, doorstop_bytes = plan_doorstop(game)
    proxy = safe_target(game, "version.dll")
    backup = safe_target(game, "version.dll.bak")
    park = proxy.exists()
    if park:
        if not proxy.is_file() or not (game / "MelonLoader").is_dir():
            raise ValueError("Unknown version.dll; refusing to disable a proxy without a MelonLoader installation")
        if backup.exists():
            raise ValueError("version.dll.bak already exists; preserve or resolve both proxies before repairing")
    actions = [f"copy {name}" for name in missing]
    if park:
        actions.append("park version.dll -> version.dll.bak")
    actions += doorstop_actions
    if dry_run:
        return actions
    require_stopped()
    for name, data in missing.items():
        target = safe_target(game, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as output:
            output.write(data)
    if park:
        os.link(proxy, backup)
        proxy.unlink()
    if doorstop_bytes is not None:
        write_doorstop(game, doorstop_bytes)
    return actions


def write_doorstop(game: Path, body: bytes) -> None:
    target = safe_target(game, DOORSTOP_FILE)
    backup = safe_target(game, f"{DOORSTOP_FILE}.bak")
    if not backup.exists():
        backup.write_bytes(target.read_bytes())
    target.write_bytes(body)
    cache = safe_target(game, STALE_ASSEMBLY_CACHE)
    if cache.is_file():
        cache.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, help="override the configured game folder")
    parser.add_argument("--pack-zip", type=Path, help="local pinned BepInExPack 6.0.788 archive")
    parser.add_argument("--download", action="store_true", help="allow downloading the pinned pack if not cached")
    parser.add_argument("--dry-run", action="store_true", help="validate and list actions without writing files")
    args = parser.parse_args(argv)
    log = None
    try:
        if not args.dry_run:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            log = LOG_FILE.open("a", encoding="utf-8")
            print(f"\nBepInEx repair: {datetime.now(UTC).isoformat()}", file=log)
        require_stopped()
        game = args.game_dir or game_dir()
        source = args.pack_zip.expanduser() if args.pack_zip else CACHE
        output = log if log is not None else sys.stdout
        print(f"Game folder: {game}", file=output)
        print(f"Pack archive: {source}", file=output)
        fetched = False
        if source.is_file():
            body = source.read_bytes()
        elif args.download and not args.pack_zip:
            body = download(PACK_URL)
            fetched = True
        else:
            raise ValueError(f"Pack ZIP not found: {source}; supply --pack-zip or allow --download")
        actions = repair(game, body, dry_run=args.dry_run)
        if fetched and not args.dry_run:
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            with CACHE.open("xb") as output:
                output.write(body)
        print("Dry run; no files changed." if args.dry_run else "Repair complete.", file=output)
        for action in actions:
            print(f"  {action}", file=output)
        if not actions:
            print("  Already repaired; no changes needed.", file=output)
        print("Launch with task game:run (supplies winhttp=n,b).", file=output)
        print("Other launchers need a winhttp native,builtin override; the registry was not changed.", file=output)
        print("Keep version.dll.bak for rollback; plugins, configuration and UserData were not changed.", file=output)
        if log is not None:
            log.flush()
            print("BepInEx repair complete." if actions else "BepInEx is already repaired; no changes needed.")
        return 0
    except (ValueError, OSError, zipfile.BadZipFile, DownloadError, MissingAsset) as exc:
        if log is not None:
            try:
                print(f"BepInEx repair failed: {exc}", file=log)
                log.flush()
            except OSError:
                pass
        print(f"BepInEx repair failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if log is not None:
            log.close()


if __name__ == "__main__":
    raise SystemExit(main())
