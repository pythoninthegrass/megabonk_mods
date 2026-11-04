"""What an install consists of, worked out before anything is written, and carried out step by step.

The plan compares the package against the game directory, so a second run does nothing, a repair
replaces only what changed or went missing, and a dry run can show the whole thing without
touching the disk.
"""

from __future__ import annotations

import shutil
import zipfile
from . import content, gamebuild, manifest as mf, proton, steam
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

RUNTIME_MODES = ("prefix", "gamedir")
OFF_VALUES = (False, 0, "off", "none", "no")


class PlanError(Exception):
    """The install cannot be planned: the package, the game, or the prefix is not in a usable state."""


@dataclass(frozen=True)
class Action:
    kind: str
    path: Path
    detail: str = ""
    source: Path | None = None

    @property
    def label(self) -> str:
        return self.detail or self.path.name

    def to_dict(self) -> dict:
        payload = {"kind": self.kind, "path": str(self.path), "detail": self.detail}
        if self.source is not None:
            payload["source"] = str(self.source)
        return payload


@dataclass(frozen=True)
class Plan:
    package: Path
    manifest: mf.PackageManifest
    game_dir: Path
    build: str
    prefix: Path | None
    runtime_mode: str
    runtime_target: Path
    dll_override: bool
    actions: tuple
    launch_option: str | None = None
    warnings: tuple = ()
    wine_override_mode: str = "auto"
    forced_tool: str | None = None

    @property
    def is_noop(self) -> bool:
        return not self.actions

    def to_dict(self) -> dict:
        return {
            "package": str(self.package),
            "package_id": self.manifest.package_id,
            "mod_version": self.manifest.mod_version,
            "melonloader_version": self.manifest.melonloader_version,
            "game_dir": str(self.game_dir),
            "build": self.build,
            "prefix": str(self.prefix) if self.prefix else None,
            "runtime_mode": self.runtime_mode,
            "runtime_target": str(self.runtime_target),
            "dll_override": self.dll_override,
            "launch_option": self.launch_option,
            "actions": [action.to_dict() for action in self.actions],
            "warnings": list(self.warnings),
        }


def _as_manifest(package: Path, manifest) -> mf.PackageManifest:
    if isinstance(manifest, mf.PackageManifest):
        return manifest
    if manifest is None:
        return mf.load_manifest(package / "manifest.json")
    return mf.load_manifest(manifest)


def _needs_copy(source: Path, target: Path, digest: str | None) -> bool:
    if not target.is_file():
        return True
    if digest:
        return mf.sha256_file(target) != digest
    return mf.sha256_file(source) != mf.sha256_file(target)


def _check_package(package: Path, manifest: mf.PackageManifest) -> None:
    problems = mf.verify_package(package)
    if problems:
        detail = "; ".join(problems[:4])
        more = f" (+{len(problems) - 4} more)" if len(problems) > 4 else ""
        raise PlanError(f"the install package does not match its manifest: {detail}{more}")


def _effective_build(game_dir: Path, requested: str | None) -> str:
    derived = gamebuild.classify_game_dir(game_dir).build
    if derived in (gamebuild.NATIVE_LINUX, gamebuild.UNKNOWN) or requested in (gamebuild.NATIVE_LINUX, gamebuild.UNKNOWN):
        raise PlanError(gamebuild.unsupported_build_message(game_dir, derived, _loader_version(game_dir)))
    return derived


def _loader_version(game_dir: Path) -> str:
    return content.installed_loader_version(game_dir) or "0.7.3"


def build_plan(
    package: Path | str,
    manifest=None,
    game: Path | str | None = None,
    *,
    build: str | None = None,
    prefix: Path | str | None = None,
    runtime_mode: str = "prefix",
    dll_override: bool | str = True,
    wine_override: str = "auto",
    forced_tool: str | None = None,
    level: Path | str | None = None,
    pack: Path | str | None = None,
    verify: bool = True,
) -> Plan:
    """Compare the package against the game and return the steps still needed."""
    package = Path(package)
    manifest = _as_manifest(package, manifest)
    if game is None:
        raise PlanError("no game directory: pass --game-dir, or install Megabonk in Steam first")
    game = Path(game)
    if verify:
        _check_package(package, manifest)
    build = _effective_build(game, build)
    if runtime_mode not in RUNTIME_MODES:
        raise PlanError(f"unknown runtime mode {runtime_mode!r} (expected {', '.join(RUNTIME_MODES)})")

    prefix = Path(prefix) if prefix else None
    want_override = dll_override not in OFF_VALUES

    warnings: list[str] = []
    mode = runtime_mode
    if mode == "prefix" and not (prefix and proton.usable_prefix(prefix)):
        mode = "gamedir"
        where = f" at {prefix}" if prefix else ""
        warnings.append(
            f"no usable Proton prefix{where}, so the .NET runtime goes beside the game; "
            "Steam needs the launch option printed at the end"
        )
        warnings.append(
            "pass --prefix <path to the pfx directory> to install into an existing Proton prefix, "
            "or launch Megabonk once in Steam under Proton so Steam creates it"
        )

    dotnet = manifest.vendor("dotnet")
    runtime_target = proton.runtime_target(prefix) if mode == "prefix" else content.runtime_dir(game)
    runtime_missing = not proton.runtime_installed(runtime_target, dotnet.version)
    launch_option = None if mode == "prefix" else proton.launch_option(runtime_target)

    actions: list[Action] = []
    actions += _loader_actions(package, manifest, game)
    actions += _file_actions(package, manifest, game)

    if runtime_missing:
        detail = f".NET {dotnet.version} into {runtime_target}"
        if launch_option:
            detail += f" (Steam launch option: {launch_option})"
        actions.append(Action("install-runtime", runtime_target, detail, source=dotnet.path(package)))

    if want_override and prefix and mode == "prefix":
        current = proton.read_dll_override(prefix, proton.DLL_NAME)
        if current != proton.DLL_VALUE or runtime_missing:
            actions.append(Action("enable-dll-override", prefix, f"version.dll = {proton.DLL_VALUE} in {prefix}"))

    if not content.levels_dir(game).is_dir():
        actions.append(Action("create-levels-dir", content.levels_dir(game), f"create {content.levels_dir(game)}"))

    if level is not None:
        actions += _level_actions(game, Path(level))
    if pack is not None:
        actions += _pack_actions(game, Path(pack))

    return Plan(
        package=package,
        manifest=manifest,
        game_dir=game,
        build=build,
        prefix=prefix,
        runtime_mode=mode,
        runtime_target=runtime_target,
        dll_override=want_override and mode == "prefix",
        actions=tuple(actions),
        launch_option=launch_option,
        warnings=tuple(warnings),
        wine_override_mode=wine_override,
        forced_tool=forced_tool,
    )


def _loader_actions(package: Path, manifest: mf.PackageManifest, game: Path) -> list[Action]:
    marker_ok = content.installed_loader_version(game) == manifest.melonloader_version
    loaded = (game / content.LOADER_DIR / "net6" / "MelonLoader.dll").is_file()
    shim = (game / "version.dll").is_file()
    if marker_ok and loaded and shim:
        return []
    loader = manifest.vendor("melonloader")
    return [Action("install-loader", game / content.LOADER_DIR, f"MelonLoader {loader.version} into {game}", source=loader.path(package))]


def _file_actions(package: Path, manifest: mf.PackageManifest, game: Path) -> list[Action]:
    actions: list[Action] = []
    for entry in manifest.files:
        source = entry.source(package)
        if not source.is_file():
            raise PlanError(f"{Path(entry.path).name} is missing from the package ({entry.path})")
        target = entry.target(game)
        if _needs_copy(source, target, entry.sha256):
            actions.append(Action("install-file", target, f"{entry.path} -> {target}", source=source))
    return actions


def _level_actions(game: Path, level: Path) -> list[Action]:
    problems = content.validate_level_file(level)
    if problems:
        raise PlanError("; ".join(problems))
    target = content.levels_dir(game) / level.name
    if target.is_file() and mf.sha256_file(target) == mf.sha256_file(level):
        return []
    return [Action("install-file", target, f"{level.name} -> {target}", source=level)]


def _pack_actions(game: Path, pack: Path) -> list[Action]:
    problems = content.validate_pack_source(pack)
    if problems:
        raise PlanError("; ".join(problems))
    dest = content.pack_dest(game, pack.name)
    actions: list[Action] = []
    for source in content.pack_files(pack):
        target = dest / source.name
        if _needs_copy(source, target, None):
            actions.append(Action("install-file", target, f"{pack.name}/{source.name} -> {target}", source=source))
    return actions


def _extract_loader(package: Path, manifest: mf.PackageManifest, game: Path) -> None:
    loader = manifest.vendor("melonloader")
    mf.verify_vendor(manifest, loader, package)
    game.mkdir(parents=True, exist_ok=True)
    root = game.resolve()
    with zipfile.ZipFile(loader.path(package)) as bundle:
        for member in bundle.infolist():
            resolved = (game / member.filename).resolve()
            if resolved != root and root not in resolved.parents:
                raise PlanError(f"{loader.name}: entry {member.filename!r} would escape the game directory")
        bundle.extractall(game)
    marker = content.version_marker(game)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(manifest.melonloader_version, encoding="utf-8")


def _wine_for(prefix: Path, mode: str, forced_tool: str | None) -> Path | None:
    if mode == "off":
        return None
    library = _library_for_prefix(prefix)
    if library is None:
        return None
    tool = proton.pick_proton(library, forced=forced_tool) or proton.pick_proton(library)
    wine = proton.proton_wine_bin(tool) if tool else None
    if wine is None and mode == "wine":
        raise PlanError(f"no wine binary found in the Proton tools under {library}; pass --proton <name> to point at the tool that has one")
    return wine


def _library_for_prefix(prefix: Path) -> Path | None:
    for parent in prefix.parents:
        if parent.name == "compatdata":
            return parent.parent.parent
    return None


def _execute(action: Action, plan: Plan) -> str | None:
    if action.kind == "install-loader":
        _extract_loader(plan.package, plan.manifest, plan.game_dir)
    elif action.kind == "install-file":
        if action.source is None:
            raise PlanError(f"no source for {action.path}")
        action.path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(action.source, action.path)
    elif action.kind == "install-runtime":
        if action.source is None:
            raise PlanError(f"no .NET runtime archive for {action.path}")
        proton.extract_runtime(action.source, action.path, version=plan.manifest.vendor("dotnet").version)
    elif action.kind == "enable-dll-override":
        wine = _wine_for(action.path, plan.wine_override_mode, plan.forced_tool)
        return proton.set_dll_override(action.path, proton.DLL_NAME, proton.DLL_VALUE, wine_bin=wine)
    elif action.kind == "create-levels-dir":
        action.path.mkdir(parents=True, exist_ok=True)
    else:
        raise PlanError(f"unknown action kind {action.kind!r}")
    return None


def apply(package: Path | str, manifest=None, game: Path | str | None = None, *, progress=None, **options) -> list[Action]:
    """Run the plan, then record what was installed. Returns the steps that were taken."""
    plan = build_plan(package, manifest, game, **options)
    return apply_plan(plan, progress=progress)


def apply_plan(plan: Plan, *, progress=None) -> list[Action]:
    """Carry out a plan the caller has already inspected, then record what was installed."""
    if progress:
        progress.start(max(len(plan.actions), 1), f"install {plan.manifest.label}")
    override_via = None
    for action in plan.actions:
        result = _execute(action, plan)
        if action.kind == "enable-dll-override":
            override_via = result
        if progress:
            progress.step(action.label)
    if plan.actions or content.load_record(plan.game_dir) is None:
        _write_record(plan, override_via)
    if progress:
        progress.finish("installed" if plan.actions else "already installed", ok=True)
    return list(plan.actions)


def _relative(game: Path, path: Path) -> str:
    try:
        return path.relative_to(game).as_posix()
    except ValueError:
        return str(path)


def _write_record(plan: Plan, override_via: str | None = None) -> None:
    game = plan.game_dir
    record = dict(content.load_record(game) or {})
    record.update(
        {
            "schema": "megabonk-levels-install/1",
            "package_id": plan.manifest.package_id,
            "mod_version": plan.manifest.mod_version,
            "melonloader_version": plan.manifest.melonloader_version,
            "game_buildid": plan.manifest.game_buildid,
            "installed_game_buildid": steam.installed_build_id(game),
            "installed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "game_dir": str(game),
        }
    )
    files = list(record.get("files", []))
    files += [Path(entry.dest).as_posix() for entry in plan.manifest.files if Path(entry.dest).as_posix() not in files]
    record["files"] = files

    levels = list(record.get("levels", []))
    for action in plan.actions:
        if action.kind == "install-file" and action.path.parent == content.levels_dir(game):
            relative = _relative(game, action.path)
            if relative not in levels:
                levels.append(relative)
    record["levels"] = levels

    packs = dict(record.get("packs", {}))
    pack_root = content.level_packs_dir(game)
    for action in plan.actions:
        if action.kind != "install-file" or action.path.parent.parent != pack_root:
            continue
        pack_id = action.path.parent.name
        entry = dict(packs.get(pack_id, {}))
        placed = list(entry.get("files", []))
        relative = _relative(game, action.path)
        if relative not in placed:
            placed.append(relative)
        entry["files"] = placed
        entry["dir"] = _relative(game, action.path.parent)
        packs[pack_id] = entry
    record["packs"] = packs

    record["runtime"] = {
        "mode": plan.runtime_mode,
        "path": str(plan.runtime_target),
        "version": plan.manifest.vendor("dotnet").version,
        "launch_option": plan.launch_option,
    }
    prefix = plan.prefix if plan.runtime_mode == "prefix" else None
    applied = bool(prefix) and proton.read_dll_override(prefix, proton.DLL_NAME) == proton.DLL_VALUE
    record["dll_override"] = {
        "applied": applied,
        "name": proton.DLL_NAME,
        "value": proton.DLL_VALUE,
        "prefix": str(prefix) if prefix else None,
        "via": override_via or ("already set" if applied else None),
    }
    content.save_record(game, record)


def uninstall(game: Path | str, *, progress=None) -> list[Path]:
    """Remove exactly what the installer recorded placing; a directory with no record is left alone."""
    game = Path(game)
    record = content.load_record(game)
    if not record:
        return []
    removed: list[Path] = []

    def remove(path: Path, tree: bool = False) -> None:
        if tree:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                if not path.exists():
                    removed.append(path)
        elif path.is_file():
            path.unlink()
            removed.append(path)

    if progress:
        steps = 5 + len(record.get("files", [])) + sum(len(entry.get("files", [])) for entry in (record.get("packs") or {}).values())
        progress.start(max(steps, 1), f"uninstall {record.get('package_id', 'MegabonkLevels')}")

    remove(game / content.LOADER_DIR, tree=True)
    remove(game / "version.dll")
    if progress:
        progress.step("MelonLoader")

    for relative in record.get("files", []):
        remove(game / relative)
    for directory in (content.MODS_DIR, content.USERLIBS_DIR):
        candidate = game / directory
        if candidate.is_dir():
            try:
                candidate.rmdir()
                removed.append(candidate)
            except OSError:
                pass
    if progress:
        progress.step("mod files")

    for relative in record.get("levels", []):
        remove(game / relative)
    for pack_id, entry in (record.get("packs") or {}).items():
        remove(game / entry["dir"] if entry.get("dir") else content.pack_dest(game, pack_id), tree=True)
    if progress:
        progress.step("levels and packs")

    runtime = record.get("runtime") or {}
    if runtime.get("path"):
        target = Path(runtime["path"])
        if (target / proton.RUNTIME_MARKER_NAME).is_file():
            remove(target, tree=True)
    if progress:
        progress.step(".NET runtime")

    override = record.get("dll_override") or {}
    if override.get("prefix"):
        prefix = Path(override["prefix"])
        if prefix.is_dir():
            library = _library_for_prefix(prefix)
            tool = proton.pick_proton(library) if library else None
            proton.clear_dll_override(prefix, proton.DLL_NAME, wine_bin=proton.proton_wine_bin(tool) if tool else None)
    if progress:
        progress.step("version.dll override")

    remove(content.record_path(game))
    if progress:
        progress.finish("uninstalled", ok=True)
    return removed
