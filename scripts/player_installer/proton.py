"""The Proton-side pieces: where .NET 6 goes in a prefix, the Wine DllOverrides entry MelonLoader needs, and which Proton tool to use.

MelonLoader hooks an Il2Cpp game through a `version.dll` next to the executable, which Wine only
loads when the registry says it is native, and the Il2Cpp interop needs a .NET 6 runtime the
prefix can find. Both are prefix state, so the installer writes them itself rather than relying
on a first launch to do it.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

RUNTIME_MARKER_NAME = "MegabonkLevels.dotnet_version"
DOTNET_FOLDER_WINDOWS = ("drive_c", "Program Files", "dotnet")
DLL_NAME = "version"
DLL_VALUE = "native,builtin"
DLL_OVERRIDES_SECTION = r"Software\Wine\DllOverrides"
HOSTFXR_SUBDIR = ("host", "fxr")
RUNTIME_HOST = "hostfxr.dll"
NUMBERS = re.compile(r"\d+")


class ProtonError(Exception):
    """A Proton or Wine step could not be completed."""


def windows_path(path: Path | str) -> str:
    """A Unix path as Wine sees it through the Z: drive."""
    text = str(path)
    if re.match(r"^[A-Za-z]:[\\/]", text):
        return text[0].upper() + ":" + text[2:].replace("/", "\\")
    return "Z:" + text.replace("/", "\\")


def runtime_target(prefix: Path | str) -> Path:
    return Path(prefix).joinpath(*DOTNET_FOLDER_WINDOWS)


def runtime_installed(target: Path | str, version: str) -> bool:
    """Whether a .NET runtime of exactly this version is sitting at target."""
    target = Path(target)
    marker = target / RUNTIME_MARKER_NAME
    if not marker.is_file() or marker.read_text(encoding="utf-8", errors="replace").strip() != version:
        return False
    hostfxr = target.joinpath(*HOSTFXR_SUBDIR, version, RUNTIME_HOST)
    return hostfxr.is_file()


def _extract_all(archive: Path | str, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    root = target.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            resolved = (target / member.filename).resolve()
            if resolved != root and root not in resolved.parents:
                raise ProtonError(f"{Path(archive).name}: entry {member.filename!r} would escape its target directory")
        bundle.extractall(target)


def extract_runtime(archive: Path | str, target: Path | str, *, version: str) -> Path:
    """Unpack a Windows .NET runtime archive and mark it as installed."""
    target = Path(target)
    _extract_all(archive, target)
    (target / RUNTIME_MARKER_NAME).write_text(version, encoding="utf-8")
    return target


def user_reg_path(prefix: Path | str) -> Path:
    return Path(prefix) / "user.reg"


def _normalise_section(section: str) -> str:
    return section.strip().strip("[]").replace("\\\\", "\\").casefold()


def _entry_line(name: str, value: str) -> str:
    return f'"{name}"="{value}"'


_ENTRY = re.compile(r'^"(?P<name>[^"]+)"\s*=\s*(?:\([^)]*\)\s*)?"(?P<value>.*)"\s*$')
_SECTION = re.compile(r"^\[(?P<section>.+)\](?:\s+\d+)?\s*$")


def _section_name(line: str) -> str | None:
    """The normalised name of a .reg section header line.

    A real Proton user.reg trails every header with a unix timestamp
    ("[Software\\\\Wine\\\\DllOverrides] 1793463301"), so accepting the
    optional trailing number is what lets the installer see sections Wine wrote.
    """
    match = _SECTION.match(line.strip())
    return _normalise_section(match.group("section")) if match else None


def _lines(prefix: Path | str) -> list[str] | None:
    path = user_reg_path(prefix)
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def read_dll_override(prefix: Path | str, name: str = DLL_NAME, *, section: str = DLL_OVERRIDES_SECTION) -> str | None:
    """The DllOverrides value Wine has for a DLL name, or None when it has none."""
    lines = _lines(prefix)
    if lines is None:
        return None
    wanted = _normalise_section(section)
    inside = False
    for line in lines:
        stripped = line.strip()
        seen = _section_name(stripped)
        if seen is not None:
            inside = seen == wanted
            continue
        if not inside:
            continue
        match = _ENTRY.match(stripped)
        if match and match.group("name").casefold() == name.casefold():
            return match.group("value")
    return None


def set_dll_override(
    prefix: Path | str,
    name: str,
    value: str,
    *,
    section: str = DLL_OVERRIDES_SECTION,
    wine_bin: Path | str | None = None,
    runner=None,
) -> str:
    """Point Wine at the game directory's DLL. Returns "wine" or "registry" for how it was done."""
    if wine_bin is not None:
        argv = _reg_add_argv(Path(wine_bin), name, value, section)
        env = dict(os.environ, WINEPREFIX=str(prefix), WINEDEBUG="-all")
        run = runner or _run
        try:
            if run(argv, env) == 0:
                return "wine"
        except OSError:
            pass
    _set_in_registry(prefix, name, value, section)
    return "registry"


def clear_dll_override(
    prefix: Path | str,
    name: str,
    *,
    section: str = DLL_OVERRIDES_SECTION,
    wine_bin: Path | str | None = None,
    runner=None,
) -> str:
    """Remove a DllOverrides entry the installer added."""
    if wine_bin is not None:
        argv = _reg_delete_argv(Path(wine_bin), name, section)
        env = dict(os.environ, WINEPREFIX=str(prefix), WINEDEBUG="-all")
        run = runner or _run
        try:
            if run(argv, env) == 0:
                return "wine"
        except OSError:
            pass
    _clear_in_registry(prefix, name, section)
    return "registry"


def _reg_key(section: str) -> str:
    return "HKCU\\" + section.strip().strip("[]")


def _reg_add_argv(wine_bin: Path, name: str, value: str, section: str) -> list[str]:
    return [str(wine_bin), "reg", "add", _reg_key(section), "/v", name, "/d", value, "/f"]


def _reg_delete_argv(wine_bin: Path, name: str, section: str) -> list[str]:
    return [str(wine_bin), "reg", "delete", _reg_key(section), "/v", name, "/f"]


def _run(argv: list[str], env: dict[str, str]) -> int:
    try:
        return subprocess.run(argv, env=env, capture_output=True, text=True, timeout=120, check=False).returncode
    except (OSError, subprocess.SubprocessError):
        return 1


def _set_in_registry(prefix: Path | str, name: str, value: str, section: str) -> None:
    lines = _lines(prefix)
    entry = _entry_line(name, value)
    wanted = _normalise_section(section)
    if lines is None:
        user_reg_path(prefix).parent.mkdir(parents=True, exist_ok=True)
        user_reg_path(prefix).write_text(f"REGEDIT4\n\n[{section.strip().strip('[]')}]\n{entry}\n", encoding="utf-8")
        return
    inside = False
    out: list[str] = []
    replaced = False
    for line in lines:
        stripped = line.strip()
        seen = _section_name(stripped)
        if seen is not None:
            if inside and not replaced:
                out.append(entry)
                replaced = True
            inside = seen == wanted
            out.append(line)
            continue
        if inside and not replaced:
            match = _ENTRY.match(stripped)
            if match and match.group("name").casefold() == name.casefold():
                out.append(entry)
                replaced = True
                continue
        out.append(line)
    if inside and not replaced:
        out.append(entry)
        replaced = True
    if not replaced:
        if out and out[-1].strip():
            out.append("")
        out.extend([_header_for(lines, section), entry])
    user_reg_path(prefix).write_text("\n".join(out) + "\n", encoding="utf-8")


def _header_for(lines: list[str], section: str) -> str:
    """A new section header in the file's own style: Wine's user.reg escapes backslashes in key
    names, a hand-written REGEDIT4 file does not."""
    body = section.strip().strip("[]")
    if lines and lines[0].strip().upper().startswith("WINE REGISTRY"):
        body = body.replace("\\", "\\\\")
    return f"[{body}]"


def _clear_in_registry(prefix: Path | str, name: str, section: str) -> None:
    lines = _lines(prefix)
    if lines is None:
        return
    inside = False
    wanted = _normalise_section(section)
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        seen = _section_name(stripped)
        if seen is not None:
            inside = seen == wanted
            out.append(line)
            continue
        if inside:
            match = _ENTRY.match(stripped)
            if match and match.group("name").casefold() == name.casefold():
                continue
        out.append(line)
    user_reg_path(prefix).write_text("\n".join(out) + "\n", encoding="utf-8")


def proton_roots(library: Path | str) -> list[Path]:
    """Steam's own Proton builds and any compatibility tool the user dropped in."""
    library = Path(library)
    directories = [library / "steamapps" / "common", library / "compatibilitytools.d"]
    tools: list[Path] = []
    for directory in directories:
        if not directory.is_dir():
            continue
        try:
            children = sorted(directory.iterdir())
        except OSError:
            continue
        tools.extend(child for child in children if child.is_dir() and child.name.casefold().startswith("proton"))
    return tools


def _version_key(tool: Path) -> tuple:
    return tuple(int(number) for number in NUMBERS.findall(tool.name))


def _matches_forced(tool: Path, forced: str) -> bool:
    def normalise(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_")

    needle = normalise(forced)
    haystack = normalise(tool.name)
    if not needle:
        return False
    return all(token in haystack.split("_") or token in haystack for token in needle.split("_"))


def pick_proton(library: Path | str, forced: str | None = None) -> Path | None:
    """The compatibility tool to use: the forced one when named, else the newest numbered Proton."""
    tools = proton_roots(library)
    if not tools:
        return None
    if forced:
        matches = [tool for tool in tools if _matches_forced(tool, forced)]
        if matches:
            needle = re.sub(r"[^a-z0-9]+", "_", forced.casefold()).strip("_")
            return max(matches, key=lambda tool: (tool.name.casefold().replace("-", "_").startswith(needle), _version_key(tool), tool.name))
        return None
    return max(tools, key=lambda tool: (_version_key(tool), tool.name))


def proton_wine_bin(tool: Path | str) -> Path | None:
    """The wine binary inside a Proton tool, for registry edits."""
    bin_dir = Path(tool) / "files" / "bin"
    for name in ("wine64", "wine"):
        candidate = bin_dir / name
        if candidate.is_file():
            return candidate
    return None


def launch_option(runtime_dir: Path | str, extra: tuple[str, ...] = ()) -> str:
    """The Steam launch option that points .NET at a runtime outside the prefix."""
    assignments = [f"DOTNET_ROOT={windows_path(runtime_dir)}", *extra]
    return " ".join([*assignments, "%command%"])


def usable_prefix(prefix: Path | str) -> bool:
    """Whether Steam has created this prefix yet (it does so on the first Proton launch)."""
    return (Path(prefix) / "drive_c").is_dir()


def remove_runtime(target: Path | str) -> bool:
    """Delete an extracted runtime; True when something was removed."""
    target = Path(target)
    if not target.exists():
        return False
    shutil.rmtree(target, ignore_errors=True)
    return not target.exists()
