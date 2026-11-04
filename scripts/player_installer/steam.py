"""Finding Steam and the Megabonk install on a Linux machine.

Covers the layouts the installer has to cope with: a native Steam client, a Flatpak
client whose data lives under ~/.var, libraries on internal disks and on removable
media, and the Proton prefix Steam keeps per library.
"""

from __future__ import annotations

import os
import subprocess
from . import vdf
from dataclasses import dataclass
from pathlib import Path

APP_ID = "3405340"
GAME_NAME = "Megabonk"
GAME_EXE = "Megabonk.exe"
NATIVE_EXE = "Megabonk.x86_64"
DATA_DIR = "Megabonk_Data"
STEAM_ROOT_NAMES = ("Steam", "steam")
FLATPAK_ID = "com.valvesoftware.Steam"
CLIENT_MARKERS = ("steamapps",)
SCAN_DEPTH = 2
FLATPAK_BINARIES = ("flatpak", "/usr/bin/flatpak", "/var/lib/flatpak/exports/bin/flatpak")

REASON_MISSING = "does not exist"
REASON_NO_STEAMAPPS = "no steamapps/ directory"
REASON_DUPLICATE = "already searched via an earlier candidate"
REASON_UNMOUNTED = "drive not attached ({parent} is missing)"
REASON_NOT_MEGABONK = "an Il2Cpp install (GameAssembly.dll) but no Megabonk.exe, Megabonk.x86_64 or Megabonk_Data/"
REASON_NO_PREFIX = "no steamapps/compatdata prefix in this library"
REASON_NO_DRIVE_C = "the prefix has no drive_c/: the game has never been launched under Proton in this library"

GAME_ASSEMBLY = "GameAssembly.dll"
UNITY_PLAYER = "UnityPlayer.dll"
IDENTITY_MARKERS = (GAME_EXE, NATIVE_EXE, DATA_DIR)


@dataclass(frozen=True)
class SteamClient:
    kind: str
    root: Path


@dataclass(frozen=True)
class LibraryRoot:
    path: Path
    source: str
    client: SteamClient | None = None
    granted: bool | None = None


@dataclass(frozen=True)
class Candidate:
    path: Path
    kind: str
    accepted: bool
    reason: str
    granted: bool | None = None
    client: SteamClient | None = None


@dataclass(frozen=True)
class GameCandidate:
    """A directory discovery thought might hold Megabonk, and what it decided."""

    path: Path
    library: Path
    how: str
    accepted: bool
    reason: str


@dataclass(frozen=True)
class PrefixCandidate:
    """A per-library compatdata prefix, and whether Steam has created it."""

    path: Path
    library: Path
    accepted: bool
    reason: str


@dataclass(frozen=True)
class FlatpakProbe:
    paths: tuple[Path, ...]
    source: str
    cli_found: bool


def _is_dir(path: Path) -> bool:
    """is_dir without the PermissionError pathlib re-raises for EACCES."""
    try:
        return path.is_dir()
    except OSError:
        return False


def _is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def _exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


def _client_candidate_list(
    home: Path | str,
    xdg_data_home: Path | str | None = None,
    granted_paths: list[Path] | None = None,
) -> list[Candidate]:
    home = Path(home).expanduser()
    data_homes: list[Path] = []
    if xdg_data_home:
        data_homes.append(Path(xdg_data_home).expanduser())
    configured = os.environ.get("XDG_DATA_HOME")
    if configured:
        configured_path = Path(configured).expanduser()
        data_homes.append(configured_path if configured_path.is_absolute() else home / configured_path)
    data_homes.append(home / ".local" / "share")
    candidates: list[tuple[str, Path]] = [(kind, path) for kind, path in (
        ("native", data_home / "Steam") for data_home in data_homes
    )]
    candidates += [
        ("native", home / ".steam" / "root"),
        ("native", home / ".steam" / "steam"),
        ("flatpak", home / ".var" / "app" / FLATPAK_ID / ".local" / "share" / "Steam"),
        ("flatpak", home / ".var" / "app" / FLATPAK_ID / "data" / "Steam"),
    ]
    candidates += [("flatpak", Path(path).expanduser()) for path in granted_paths or []]
    out: list[Candidate] = []
    seen: set[Path] = set()
    for kind, candidate in candidates:
        if not _is_dir(candidate):
            out.append(Candidate(candidate, kind, False, REASON_MISSING))
            continue
        if not all(_exists(candidate / marker) for marker in CLIENT_MARKERS):
            out.append(Candidate(candidate, kind, False, REASON_NO_STEAMAPPS))
            continue
        key = _identity(candidate)
        if key in seen:
            out.append(Candidate(candidate, kind, False, REASON_DUPLICATE))
            continue
        seen.add(key)
        out.append(Candidate(candidate, kind, True, ""))
    return out


def client_candidates(
    home: Path | str,
    xdg_data_home: Path | str | None = None,
    granted_paths: list[Path] | None = None,
) -> list[Candidate]:
    """Every client location considered, each with the reason it was accepted or rejected."""
    return _client_candidate_list(home, xdg_data_home, granted_paths)


def client_roots(
    home: Path | str,
    xdg_data_home: Path | str | None = None,
    granted_paths: list[Path] | None = None,
) -> list[SteamClient]:
    """Steam clients for a user: native first, then Flatpak, whose root may sit in a granted path rather than under ~/.var."""
    return [SteamClient(c.kind, c.path) for c in _client_candidate_list(home, xdg_data_home, granted_paths) if c.accepted]


def flatpak_override_paths(text: str, home: Path | str | None = None) -> list[Path]:
    """Absolute paths a Flatpak Steam is allowed to read, from `flatpak override --show` output."""
    home = Path(home).expanduser() if home else Path.home()
    in_context = False
    paths: list[Path] = []
    seen: set[Path] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            in_context = line == "[Context]"
            continue
        if not in_context or not line.startswith("filesystems="):
            continue
        for entry in line.split("=", 1)[1].split(";"):
            entry = entry.strip()
            if not entry or entry.startswith("!"):
                continue
            path = _expand_flatpak_path(entry, home)
            if path is None or path in seen:
                continue
            seen.add(path)
            paths.append(path)
    return paths


def _expand_flatpak_path(entry: str, home: Path) -> Path | None:
    if entry in {"host", "host-os", "host-etc", "home", "os", "etc"} or entry.startswith(("host-", "xdg-", "home/")):
        return None
    if entry == "~":
        return home
    if entry.startswith("~/"):
        return home / entry[2:]
    path = Path(entry)
    return path if path.is_absolute() else home / path


def _flatpak_override_file(home: Path) -> Path | None:
    path = home / ".var" / "app" / FLATPAK_ID / "configuration" / "flatpak" / "local-overrides" / FLATPAK_ID
    return path if _is_file(path) else None


def flatpak_probe(home: Path | str) -> FlatpakProbe:
    """How the Flatpak grants were answered: the persisted file, the CLI, or neither."""
    home = Path(home).expanduser()
    stored = _flatpak_override_file(home)
    if stored is not None:
        try:
            paths = flatpak_override_paths(stored.read_text(encoding="utf-8", errors="replace"), home=home)
            return FlatpakProbe(tuple(paths), "file", True)
        except OSError:
            pass
    cli_found = False
    for binary in FLATPAK_BINARIES:
        try:
            proc = subprocess.run(
                [binary, "override", "--show", FLATPAK_ID],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        cli_found = True
        if proc.returncode == 0 and proc.stdout:
            return FlatpakProbe(tuple(flatpak_override_paths(proc.stdout, home=home)), "cli", True)
    return FlatpakProbe((), "none", cli_found)


def flatpak_granted_paths(home: Path | str) -> list[Path]:
    """Paths Flatpak Steam may read, from the persisted override file or the flatpak CLI."""
    return list(flatpak_probe(home).paths)


def libraryfolders(client: SteamClient) -> list[Path]:
    path = client.root / "steamapps" / "libraryfolders.vdf"
    if not _is_file(path):
        return []
    try:
        data = vdf.load_vdf(path)
    except vdf.VdfError:
        return []
    return [Path(value) for value in vdf.library_folder_paths(data)]


def _library_candidate_list(
    clients: list[SteamClient],
    *,
    overrides: list[Path] | None = None,
    extra_paths: list[Path] | None = None,
    mount_roots: list[Path] | None = None,
    include_missing: bool = False,
) -> list[Candidate]:
    found: list[Candidate] = []
    seen: set[Path] = set()
    granted_paths = list(overrides or [])
    granted = {granted_path for granted_path in granted_paths}

    def add(path: Path, source: str, client: SteamClient | None = None, granted: bool | None = None) -> None:
        path = Path(path)
        if not include_missing and not _plausible(path):
            found.append(Candidate(path, source, False, REASON_UNMOUNTED.format(parent=path.parent), granted, client))
            return
        key = _identity(path)
        if key in seen:
            found.append(Candidate(path, source, False, REASON_DUPLICATE, granted, client))
            return
        seen.add(key)
        found.append(Candidate(path, source, True, "", granted, client))

    for client in clients:
        for path in libraryfolders(client):
            add(path, "client", client, granted=True if path in granted else (False if client.kind == "flatpak" else None))

    for path in granted_paths:
        add(path, "flatpak-override", granted=True)

    for path in extra_paths or []:
        add(Path(path), "explicit", granted=None)

    for mount in mount_roots or []:
        for path in scan_for_libraries(mount):
            add(path, "scan")
    return found


def library_candidates(
    clients: list[SteamClient],
    *,
    overrides: list[Path] | None = None,
    extra_paths: list[Path] | None = None,
    mount_roots: list[Path] | None = None,
    include_missing: bool = False,
) -> list[Candidate]:
    """Every library considered, each with the reason it was accepted or rejected."""
    return _library_candidate_list(
        clients,
        overrides=overrides,
        extra_paths=extra_paths,
        mount_roots=mount_roots,
        include_missing=include_missing,
    )


def library_roots(
    clients: list[SteamClient],
    *,
    overrides: list[Path] | None = None,
    extra_paths: list[Path] | None = None,
    mount_roots: list[Path] | None = None,
    include_missing: bool = False,
) -> list[LibraryRoot]:
    """Libraries to search, in priority order: the client's own list, Flatpak grants, explicit paths, then a media scan."""
    return [
        LibraryRoot(candidate.path, candidate.kind, candidate.client, candidate.granted)
        for candidate in _library_candidate_list(
            clients,
            overrides=overrides,
            extra_paths=extra_paths,
            mount_roots=mount_roots,
            include_missing=include_missing,
        )
        if candidate.accepted
    ]


def scan_for_libraries(mount_root: Path | str, depth: int = SCAN_DEPTH) -> list[Path]:
    """Directories under a mount point that look like a Steam library (they hold steamapps/common)."""
    mount_root = Path(mount_root)
    if not _is_dir(mount_root):
        return []
    found: list[Path] = []
    frontier = [mount_root]
    for _ in range(depth):
        nxt: list[Path] = []
        for directory in frontier:
            try:
                children = sorted(child for child in directory.iterdir() if _is_dir(child))
            except OSError:
                continue
            for child in children:
                if child.name.startswith("."):
                    continue
                if _is_dir(child / "steamapps" / "common"):
                    found.append(child)
                else:
                    nxt.append(child)
        frontier = nxt
    return found


def _is_megabonk(directory: Path) -> bool:
    """Only Megabonk names itself: its executables and data directory are game-specific."""
    if not _is_dir(directory):
        return False
    if any(_is_file(directory / marker) for marker in (GAME_EXE, NATIVE_EXE)):
        return True
    return _is_dir(directory / DATA_DIR)


def _is_il2cpp(directory: Path) -> bool:
    """Any Unity/Il2Cpp install: proof a folder is a game, but not proof of which one."""
    return _is_dir(directory) and _is_file(directory / GAME_ASSEMBLY)


def _common_children(library: Path) -> list[Path]:
    common = library / "steamapps" / "common"
    if not _is_dir(common):
        return []
    try:
        return sorted(child for child in common.iterdir() if _is_dir(child))
    except OSError:
        return []


def game_candidates(roots: list[LibraryRoot], game_name: str = GAME_NAME) -> list[GameCandidate]:
    """Every directory discovery offered as Megabonk, in the order it should be trusted.

    Steam's own app manifest first, then the folder name Steam creates, then any other
    Il2Cpp install in the library. Nothing is accepted on layout alone: an unrelated
    Il2Cpp game shares the shape of a Megabonk install and must never be installed into.
    """
    out: list[GameCandidate] = []
    seen: set[str] = set()

    def take(directory: Path, library: Path, how: str) -> None:
        key = _identity(directory)
        if key in seen:
            return
        seen.add(key)
        if not _exists(directory):
            out.append(GameCandidate(directory, library, how, False, REASON_MISSING))
        elif _is_megabonk(directory):
            out.append(GameCandidate(directory, library, how, True, ""))
        else:
            out.append(GameCandidate(directory, library, how, False, REASON_NOT_MEGABONK))

    for root in roots:
        install_dir = _install_dir_from_manifests(root.path, game_name)
        if install_dir is not None:
            take(install_dir, root.path, "manifest")
    for root in roots:
        named = root.path / "steamapps" / "common" / game_name
        if _is_dir(named):
            take(named, root.path, "name")
    for root in roots:
        for child in _common_children(root.path):
            if _is_megabonk(child) or _is_il2cpp(child):
                take(child, root.path, "scan")
    return out


def find_game_dir(roots: list[LibraryRoot], game_name: str = GAME_NAME) -> Path | None:
    """The first library holding a Megabonk install, by its own files rather than its shape."""
    for candidate in game_candidates(roots, game_name):
        if candidate.accepted:
            return candidate.path
    return None


def _install_dir_from_manifests(library: Path, game_name: str) -> Path | None:
    """The folder Steam's own appmanifest says holds this app, when the manifest says so."""
    steamapps = library / "steamapps"
    if not _is_dir(steamapps):
        return None
    try:
        manifests = sorted(steamapps.glob(f"appmanifest_{APP_ID}.acf"))
    except OSError:
        return None
    for manifest in manifests:
        try:
            data = vdf.load_vdf(manifest)
        except vdf.VdfError:
            continue
        app_ids = [str(value) for value in vdf.find_all(data, ("*", "appid"))]
        if app_ids and APP_ID not in app_ids:
            continue
        install = next(
            (value for value in vdf.find_all(data, ("*", "installdir")) if isinstance(value, str) and value.strip()),
            None,
        )
        if install:
            return steamapps / "common" / str(install)
    return None


def installed_build_id(game_dir: Path | str) -> str | None:
    """The depot build id Steam's appmanifest records for the install, or None when it records none."""
    library = _library_of_game_dir(Path(game_dir))
    if library is None:
        return None
    manifest = library / "steamapps" / f"appmanifest_{APP_ID}.acf"
    try:
        data = vdf.load_vdf(manifest)
    except (OSError, vdf.VdfError):
        return None
    return next(
        (str(value).strip() for value in vdf.find_all(data, ("*", "buildid")) if str(value).strip()),
        None,
    )


def prefix_root(library: Path | str, app_id: str = APP_ID) -> Path:
    return Path(library) / "steamapps" / "compatdata" / app_id / "pfx"


def _library_of_game_dir(game_dir: Path) -> Path | None:
    for parent in game_dir.parents:
        if parent.name == "common":
            return parent.parent.parent
    return None


def prefix_candidates(libraries: list[Path | str], app_id: str = APP_ID) -> list[PrefixCandidate]:
    """Each library's compatdata prefix for this app, and whether Steam has filled it in."""
    out: list[PrefixCandidate] = []
    seen: set[str] = set()
    for library in libraries:
        library = Path(library)
        key = _identity(library)
        if key in seen:
            continue
        seen.add(key)
        prefix = prefix_root(library, app_id)
        if not _is_dir(prefix):
            out.append(PrefixCandidate(prefix, library, False, REASON_NO_PREFIX))
        elif not _is_dir(prefix / "drive_c"):
            out.append(PrefixCandidate(prefix, library, False, REASON_NO_DRIVE_C))
        else:
            out.append(PrefixCandidate(prefix, library, True, ""))
    return out


def find_prefix(
    game_dir: Path | str,
    libraries: list[Path | str],
    app_id: str = APP_ID,
) -> tuple[Path | None, list[PrefixCandidate]]:
    """The prefix to install into, plus every prefix considered.

    Steam keeps the prefix in the library the game was installed to, which is not always the
    one holding the game files today. When the game's own library has no usable prefix, the
    only other usable one is taken; two of them is a guess, so nothing is chosen.
    """
    game_dir = Path(game_dir)
    own = prefix_for_game_dir(game_dir, app_id)
    own_library = _library_of_game_dir(game_dir)
    libraries = [Path(library) for library in libraries]
    if own_library is not None and any(_identity(path) == _identity(own_library) for path in libraries):
        libraries = [own_library] + [path for path in libraries if _identity(path) != _identity(own_library)]
    considered = prefix_candidates(libraries, app_id)
    if own is not None and _is_dir(own / "drive_c"):
        return own, considered
    others = [candidate for candidate in considered if candidate.accepted and candidate.path != own]
    if len(others) == 1:
        return others[0].path, considered
    if len(others) > 1:
        return None, considered
    return own, considered


def prefix_for_game_dir(game_dir: Path | str, app_id: str = APP_ID) -> Path | None:
    """The compatdata prefix that belongs to an install, when the library layout is Steam's."""
    game_dir = Path(game_dir)
    for parent in game_dir.parents:
        if parent.name == "common":
            library = parent.parent.parent
            candidate = prefix_root(library, app_id)
            if _is_dir(candidate):
                return candidate
            return None
    return None


def compatdata_root(game_dir: Path | str, app_id: str = APP_ID) -> Path | None:
    prefix = prefix_for_game_dir(game_dir, app_id)
    return prefix.parent if prefix else None


def localconfig(client: SteamClient) -> dict | None:
    path = client.root / "config" / "localconfig.vdf"
    if not _is_file(path):
        return None
    try:
        return vdf.load_vdf(path)
    except vdf.VdfError:
        return None


STEAM_PROCESS_MARKERS = ("/Steam/ubuntu12_32/steam", "/steamapps/common/SteamLinuxRuntime", "com.valvesoftware.Steam", "steamwebhelper")


def steam_running() -> bool:
    """Whether a Steam client is running, which is when it rewrites localconfig.vdf."""
    try:
        proc = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    return any(marker in line for line in proc.stdout.splitlines() for marker in STEAM_PROCESS_MARKERS)


def _plausible(path: Path) -> bool:
    """A library is worth searching when it exists, or its parent does: a parent that is gone too means the drive is not attached."""
    return _is_dir(path) or _is_dir(path.parent)


def _identity(path: Path) -> str:
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    try:
        stat = resolved.stat()
        return f"{stat.st_dev}:{stat.st_ino}"
    except OSError:
        return str(resolved)
