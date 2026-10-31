"""Command-line entry point: `python3 -m player_installer` (or the install.sh wrapper).

Resolves Steam, the game install and its Proton prefix, checks the package, then installs,
repairs, checks, or uninstalls. Exit codes are stable so a desktop shortcut or script can act
on them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from . import content, gamebuild, manifest as mf, plan, proton, steam, ui
from pathlib import Path

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_NOT_FOUND = 3
EXIT_UNSUPPORTED_BUILD = 4
EXIT_OUT_OF_DATE = 10

MOUNT_ROOTS = ("/media", "/run/media", "/mnt", "/Volumes")
DOTNET_IN_MODES = {"prefix": "prefix", "gamedir": "gamedir"}
WINE_OVERRIDE_MODES = ("auto", "registry", "wine", "off")
LOG_HINT = "MelonLoader/Latest.log"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="player_installer",
        description="Install MelonLoader and the MegabonkLevels map editor on Linux (Steam Play / Proton).",
    )
    parser.add_argument("--package", help="the unzipped MegabonkLevels player package directory")
    parser.add_argument("--python", dest="python", default=None, help="the interpreter install.sh chose; accepted so the flag survives the wrapper")
    parser.add_argument("--home", help="home directory to search for Steam (default: $HOME)")
    parser.add_argument("--game-dir", help="install straight into this Megabonk folder, skipping Steam discovery")
    parser.add_argument("--prefix", help="Proton prefix to write the .NET runtime and version.dll override into")
    parser.add_argument("--library", action="append", default=[], help="extra Steam library folder to search (repeatable)")
    parser.add_argument("--level", action="append", default=[], help="a .mblevel.json file to add to UserData/Levels (repeatable)")
    parser.add_argument("--pack", action="append", default=[], help="a level-pack directory to install (repeatable)")
    parser.add_argument("--dotnet-in", choices=sorted(DOTNET_IN_MODES), default="prefix", help="where the .NET 6 runtime goes")
    parser.add_argument("--wine-override", choices=WINE_OVERRIDE_MODES, default="auto", help="how to set version.dll = native,builtin")
    parser.add_argument("--proton", help="force a named Proton compatibility tool when looking for wine")
    parser.add_argument("--no-gui", action="store_true", help="never open a progress dialog")
    parser.add_argument("--check", action="store_true", help="report drift instead of changing anything")
    parser.add_argument("--dry-run", action="store_true", help="print what would be done and change nothing")
    parser.add_argument("--uninstall", action="store_true", help="remove what this installer placed")
    parser.add_argument("--json", action="store_true", dest="as_json", help="machine-readable output on stdout")
    return parser


class Reporter:
    def __init__(self, as_json: bool = False) -> None:
        self.as_json = as_json

    def say(self, message: str = "") -> None:
        if not self.as_json:
            print(message, flush=True)

    def warn(self, message: str) -> None:
        print(f"warning: {message}", file=sys.stderr, flush=True)

    def problem(self, message: str) -> None:
        print(f"  - {message}", file=sys.stderr, flush=True)

    def fail(self, message: str, code: int) -> int:
        print(message, file=sys.stderr, flush=True)
        return code


def resolve_package_dir(raw: str) -> Path | None:
    """The folder holding manifest.json, tolerating the extra directory a zip usually extracts to."""
    candidate = Path(raw).expanduser()
    if (candidate / "manifest.json").is_file():
        return candidate
    if candidate.is_dir():
        for child in sorted(candidate.iterdir()):
            if child.is_dir() and (child / "manifest.json").is_file():
                return child
    return None


def find_install(home: Path, extra_libraries: list[str], reporter: Reporter) -> tuple[Path | None, Path | None, list[str]]:
    granted = steam.flatpak_granted_paths(home)
    clients = steam.client_roots(home, granted_paths=granted)
    if granted:
        reporter.say("Flatpak Steam may only read: " + ", ".join(str(path) for path in granted))
    roots = steam.library_roots(
        clients,
        overrides=granted,
        extra_paths=[Path(path).expanduser() for path in extra_libraries],
        mount_roots=[Path(root) for root in MOUNT_ROOTS if Path(root).is_dir()],
    )
    if not roots:
        reporter.say("no Steam library found; pass --game-dir if Megabonk is somewhere unusual")
    game_dir = steam.find_game_dir(roots)
    if game_dir is None:
        return None, None, [str(root.path) for root in roots]
    return game_dir, steam.prefix_for_game_dir(game_dir), [str(root.path) for root in roots]


def validate_inputs(args: argparse.Namespace, reporter: Reporter) -> list[str]:
    problems: list[str] = []
    for raw in args.level:
        problems += content.validate_level_file(Path(raw).expanduser())
    for raw in args.pack:
        problems += content.validate_pack_source(Path(raw).expanduser())
    for problem in problems:
        reporter.problem(problem)
    return problems


def _launch_option_note(plan_value: plan.Plan) -> str:
    return (
        "Steam > Library > Megabonk > Properties, then paste this into Launch Options:\n\n"
        f"    {plan_value.launch_option}\n\n"
        "Steam rewrites its own config while it runs, so the installer cannot set this for you."
    )


def do_check(args: argparse.Namespace, reporter: Reporter, game_dir: Path, package: Path, manifest: mf.PackageManifest) -> int:
    result = plan.build_plan(
        package,
        manifest,
        game_dir,
        prefix=_prefix(args, game_dir),
        runtime_mode=DOTNET_IN_MODES[args.dotnet_in],
        dll_override=args.wine_override,
        wine_override=args.wine_override,
        forced_tool=args.proton,
        level=_single(args.level),
        pack=_single(args.pack),
        verify=False,
    )
    if not result.actions:
        reporter.say("nothing to do — the install matches the package")
        if reporter.as_json:
            print(json.dumps({"ok": True, "drift": [], **result.to_dict()}, indent=2))
        return EXIT_OK
    reporter.say(f"{len(result.actions)} thing(s) are out of date with package {manifest.package_id}:")
    for action in result.actions:
        reporter.say(f"  - {action.kind}: {action.path}")
    if reporter.as_json:
        print(json.dumps({"ok": False, "drift": [action.to_dict() for action in result.actions], **result.to_dict()}, indent=2))
    return EXIT_OUT_OF_DATE


def _single(values: list[str]) -> Path | None:
    return Path(values[-1]).expanduser() if values else None


def _prefix(args: argparse.Namespace, game_dir: Path) -> Path | None:
    if args.prefix:
        return Path(args.prefix).expanduser()
    return steam.prefix_for_game_dir(game_dir)


def do_install(args: argparse.Namespace, reporter: Reporter, game_dir: Path, package: Path, manifest: mf.PackageManifest) -> int:
    options = {
        "prefix": _prefix(args, game_dir),
        "runtime_mode": DOTNET_IN_MODES[args.dotnet_in],
        "dll_override": args.wine_override,
        "wine_override": args.wine_override,
        "forced_tool": args.proton,
        "level": _single(args.level),
        "pack": _single(args.pack),
        "verify": False,
    }
    result = plan.build_plan(package, manifest, game_dir, **options)
    for warning in result.warnings:
        reporter.warn(warning)

    if reporter.as_json and (args.dry_run or result.is_noop):
        print(json.dumps({"ok": True, "dry_run": bool(args.dry_run), **result.to_dict()}, indent=2))
        return EXIT_OK

    if args.dry_run:
        if not result.actions:
            reporter.say("nothing to do — the install already matches the package")
        else:
            reporter.say(f"would do {len(result.actions)} thing(s) to {game_dir}:")
            for action in result.actions:
                reporter.say(f"  - {action.kind}: {action.label}")
        return EXIT_OK

    progress = ui.pick_progress(
        dict(os.environ),
        force_text=args.no_gui or args.as_json,
        writer=(lambda line: None) if args.as_json else None,
    )
    taken = plan.apply_plan(result, progress=progress)
    if reporter.as_json:
        print(json.dumps({"ok": True, "dry_run": False, "taken": [action.to_dict() for action in taken], **result.to_dict()}, indent=2))
    else:
        _report_install(reporter, result, taken, manifest)
    return EXIT_OK


def _report_install(reporter: Reporter, result: plan.Plan, taken: list[plan.Action], manifest: mf.PackageManifest) -> None:
    if not taken:
        reporter.say(f"nothing to do — {manifest.label} is already installed and matches package {manifest.package_id}")
    else:
        reporter.say(f"installed {manifest.label} ({len(taken)} step(s))")
    for action in taken:
        reporter.say(f"  {action.kind}: {action.path}")
    if not taken:
        for entry in manifest.files:
            reporter.say(f"  already in place: {result.game_dir / entry.dest}")
    if result.launch_option:
        reporter.say("")
        reporter.say(_launch_option_note(result))
    record = content.load_record(result.game_dir)
    if record:
        reporter.say("")
        for line in content.describe_record(record):
            reporter.say(f"  {line}")
    reporter.say("")
    reporter.say(f"Start Megabonk from Steam; the map editor loads with the game. Anything that goes wrong is in {LOG_HINT}.")


def do_uninstall(args: argparse.Namespace, reporter: Reporter, game_dir: Path) -> int:
    record = content.load_record(game_dir)
    if not record:
        reporter.say(f"nothing to uninstall: no installer record in {game_dir}")
        return EXIT_OK
    progress = ui.pick_progress(dict(os.environ), force_text=args.no_gui)
    removed = plan.uninstall(game_dir, progress=progress)
    reporter.say(f"removed {len(removed)} item(s) from {game_dir}")
    for path in removed:
        reporter.say(f"  {path}")
    if reporter.as_json:
        print(json.dumps({"ok": True, "removed": [str(path) for path in removed]}, indent=2))
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    reporter = Reporter(as_json=args.as_json)

    if args.uninstall:
        game_dir, _ = _locate(args, reporter)
        if game_dir is None:
            return EXIT_NOT_FOUND
        return do_uninstall(args, reporter, game_dir)

    if not args.package:
        return reporter.fail("no --package: point it at the unzipped MegabonkLevels download (the folder holding manifest.json)", EXIT_USAGE)
    package = resolve_package_dir(args.package)
    if package is None:
        return reporter.fail(f"{args.package} has no manifest.json — pass the unzipped download folder, not the .zip", EXIT_ERROR)
    try:
        manifest = mf.load_manifest(package / "manifest.json")
    except mf.ManifestError as exc:
        return reporter.fail(str(exc), EXIT_ERROR)

    if validate_inputs(args, reporter):
        return reporter.fail("the level or level-pack inputs are not valid — see the list above", EXIT_ERROR)

    try:
        drift = mf.verify_package(package)
    except mf.ManifestError as exc:
        return reporter.fail(str(exc), EXIT_ERROR)
    if drift:
        return reporter.fail("the package does not match its manifest:\n  " + "\n  ".join(drift), EXIT_ERROR)

    game_dir, _searched = _locate(args, reporter)
    if game_dir is None:
        return EXIT_NOT_FOUND

    build = gamebuild.classify_game_dir(game_dir)
    if not build.supported:
        return reporter.fail(gamebuild.unsupported_build_message(game_dir, build.build, manifest.melonloader_version), EXIT_UNSUPPORTED_BUILD)

    if steam.steam_running():
        reporter.warn("Steam is running — quit it first if a step looks like it did not stick")

    try:
        if args.check:
            return do_check(args, reporter, game_dir, package, manifest)
        return do_install(args, reporter, game_dir, package, manifest)
    except (plan.PlanError, mf.ManifestError, proton.ProtonError) as exc:
        return reporter.fail(str(exc), EXIT_ERROR)
    except OSError as exc:
        return reporter.fail(f"{exc}", EXIT_ERROR)


def _locate(args: argparse.Namespace, reporter: Reporter) -> tuple[Path | None, list[str]]:
    if args.game_dir:
        game_dir = Path(args.game_dir).expanduser()
        if not game_dir.is_dir():
            reporter.fail(gamebuild.unknown_build_message(game_dir), EXIT_NOT_FOUND)
            return None, []
        return game_dir, []
    home = Path(args.home).expanduser() if args.home else Path.home()
    game_dir, _prefix, searched = find_install(home, args.library, reporter)
    if game_dir is None:
        reporter.fail(
            "\n".join(
                [
                    "Megabonk was not found in any Steam library.",
                    "Install it in Steam and start it once, or point the installer straight at it:",
                    f"  python3 -m player_installer --package <package> --game-dir <path to the folder holding {gamebuild.WINDOWS_EXE}>",
                    "",
                    "Libraries searched: " + (", ".join(searched) or "none"),
                ]
            ),
            EXIT_NOT_FOUND,
        )
        return None, searched
    return game_dir, searched


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
