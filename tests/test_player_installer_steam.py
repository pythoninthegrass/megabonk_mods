"""
Self-test for scripts/player_installer/steam.py.

Steam client and library discovery across the layouts the Linux installer
supports: native Steam, Flatpak Steam with a relocated client and library, and
a library on removable media. Runs entirely against fixture trees.
"""

import player_installer.steam as steam
from pathlib import Path

LIBRARYFOLDERS = """
"libraryfolders"
{
\t"0"
\t{
\t\t"path"\t\t"{root}"
\t}
\t"1"
\t{
\t\t"path"\t\t"{second}"
\t}
}
"""


def _make_client(root: Path, library_paths: list[Path], *, with_config: bool = True) -> Path:
    (root / "steamapps").mkdir(parents=True, exist_ok=True)
    if with_config:
        (root / "config").mkdir(parents=True, exist_ok=True)
    body = "".join(
        '\t"%d"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n' % (i, p) for i, p in enumerate(library_paths)
    )
    (root / "steamapps" / "libraryfolders.vdf").write_text('"libraryfolders"\n{\n%s}\n' % body)
    return root


def _make_library(root: Path, *, with_game: bool = True, app: str = "Megabonk") -> Path:
    (root / "steamapps" / "common").mkdir(parents=True, exist_ok=True)
    if with_game:
        (root / "steamapps" / "common" / app / "Megabonk_Data").mkdir(parents=True)
    return root


def test_client_roots_finds_native_steam(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _make_client(home / ".local" / "share" / "Steam", [])
    clients = steam.client_roots(home)
    assert [c.kind for c in clients] == ["native"]
    assert clients[0].root == home / ".local" / "share" / "Steam"


def test_client_roots_dedupes_symlinked_steam_dirs(tmp_path: Path) -> None:
    home = tmp_path / "home"
    real = _make_client(home / ".local" / "share" / "Steam", [])
    link = home / ".steam" / "steam"
    link.parent.mkdir(parents=True)
    link.symlink_to(real)
    roots = [c.root.resolve() for c in steam.client_roots(home)]
    assert roots.count(real.resolve()) == 1


def test_client_roots_ignores_directories_that_are_not_a_steam_root(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / ".local" / "share" / "Steam").mkdir(parents=True)
    assert steam.client_roots(home) == []


def test_client_roots_finds_flatpak_steam(tmp_path: Path) -> None:
    home = tmp_path / "home"
    flatpak = _make_client(home / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam", [])
    clients = steam.client_roots(home)
    assert steam.SteamClient("flatpak", flatpak) in clients
    assert [c.kind for c in clients if c.kind == "flatpak"] == ["flatpak"]


def test_client_roots_honours_xdg_data_home(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _make_client(home / "games" / "Steam", [])
    clients = steam.client_roots(home, xdg_data_home=home / "games")
    assert any(c.root == home / "games" / "Steam" for c in clients)


def test_client_roots_accepts_a_granted_path_as_the_flatpak_steam_root(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    relocated = _make_client(tmp_path / "media" / "steam", [])
    assert steam.client_roots(home) == []
    assert steam.client_roots(home, granted_paths=[relocated]) == [steam.SteamClient("flatpak", relocated)]


def test_client_roots_keeps_native_first_and_does_not_repeat_a_granted_root(tmp_path: Path) -> None:
    home = tmp_path / "home"
    native = _make_client(home / ".local" / "share" / "Steam", [])
    granted = _make_client(tmp_path / "media" / "steam", [])
    clients = steam.client_roots(home, granted_paths=[granted, native])
    assert [(c.kind, c.root) for c in clients] == [("native", native), ("flatpak", granted)]


def test_flatpak_override_paths_reads_granted_filesystems() -> None:
    text = "[Context]\nfilesystems=/media/steam;\nfilesystems=!/secret;/data;\n"
    assert steam.flatpak_override_paths(text) == [Path("/media/steam"), Path("/data")]


def test_flatpak_override_paths_skips_special_tokens_and_resolves_home_relative() -> None:
    text = "[Context]\nfilesystems=host;xdg-config;~/games;relative/dir;\n"
    assert steam.flatpak_override_paths(text, home=Path("/home/lance")) == [Path("/home/lance/games"), Path("/home/lance/relative/dir")]


def test_flatpak_override_paths_ignores_other_sections_and_other_keys() -> None:
    text = "[Application]\nname=com.valvesoftware.Steam;\n[Context]\nsession-tell-filesystems=true;\nfilesystems=/ok;\n[Environment]\nfilesystems=/nope;\n"
    assert steam.flatpak_override_paths(text) == [Path("/ok")]


def test_library_roots_reads_every_client_libraryfolders(tmp_path: Path) -> None:
    client = _make_client(tmp_path / "steam", [tmp_path / "lib1", tmp_path / "lib2"])
    roots = steam.library_roots([steam.SteamClient("native", client)])
    assert [r.path for r in roots] == [tmp_path / "lib1", tmp_path / "lib2"]
    assert {r.source for r in roots} == {"client"}


def test_library_roots_skips_stale_libraries_that_are_gone(tmp_path: Path) -> None:
    client = _make_client(tmp_path / "steam", [tmp_path / "lib1", tmp_path / "mnt" / "games" / "GameLibrary" / "Steam"])
    _make_library(tmp_path / "lib1")
    roots = steam.library_roots([steam.SteamClient("native", client)])
    assert [r.path for r in roots] == [tmp_path / "lib1"]


def test_library_roots_keeps_granted_paths_without_a_vdf_entry(tmp_path: Path) -> None:
    client = _make_client(tmp_path / "steam", [])
    relocated = _make_library(tmp_path / "media" / "steam")
    roots = steam.library_roots([steam.SteamClient("native", client)], overrides=[relocated])
    assert roots[0].path == relocated
    assert roots[0].source == "flatpak-override"


def test_library_roots_finds_a_library_on_removable_media(tmp_path: Path) -> None:
    media = tmp_path / "media"
    _make_library(media / "sdcard" / "SteamLibrary")
    roots = steam.library_roots([], mount_roots=[media])
    assert [r.path for r in roots] == [media / "sdcard" / "SteamLibrary"]
    assert roots[0].source == "scan"


def test_library_roots_dedupes_and_prefers_the_first_source(tmp_path: Path) -> None:
    client = _make_client(tmp_path / "steam", [tmp_path / "lib1"])
    _make_library(tmp_path / "lib1")
    roots = steam.library_roots([steam.SteamClient("native", client)], overrides=[tmp_path / "lib1"], extra_paths=[tmp_path / "lib1"])
    assert len(roots) == 1
    assert roots[0].source == "client"


def test_library_roots_honours_explicit_path_last_resort(tmp_path: Path) -> None:
    roots = steam.library_roots([], extra_paths=[tmp_path / "nope"], include_missing=True)
    assert [r.path for r in roots] == [tmp_path / "nope"]


def test_find_game_dir_locates_the_install(tmp_path: Path) -> None:
    library = _make_library(tmp_path / "lib")
    roots = [steam.LibraryRoot(library, "client")]
    assert steam.find_game_dir(roots) == library / "steamapps" / "common" / "Megabonk"


def test_find_game_dir_prefers_an_earlier_root(tmp_path: Path) -> None:
    first = _make_library(tmp_path / "lib1")
    second = _make_library(tmp_path / "lib2")
    roots = [steam.LibraryRoot(first, "client"), steam.LibraryRoot(second, "scan")]
    assert steam.find_game_dir(roots) == first / "steamapps" / "common" / "Megabonk"


def test_find_game_dir_none_when_no_library_has_the_game(tmp_path: Path) -> None:
    library = _make_library(tmp_path / "lib", with_game=False)
    assert steam.find_game_dir([steam.LibraryRoot(library, "client")]) is None


def test_prefix_root_follows_steam_compatdata_layout(tmp_path: Path) -> None:
    assert steam.prefix_root(tmp_path / "lib", "3405340") == tmp_path / "lib" / "steamapps" / "compatdata" / "3405340" / "pfx"


def test_steam_running_detects_the_process(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(steam.subprocess, "run", lambda *a, **k: type("R", (), {"stdout": "123 /home/lance/.local/share/Steam/ubuntu12_32/steam\n"})())
    assert steam.steam_running() is True


def test_steam_running_false_when_not_in_process_list(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(steam.subprocess, "run", lambda *a, **k: type("R", (), {"stdout": "1 python3 x.py\n"})())
    assert steam.steam_running() is False


def test_steam_running_false_when_ps_is_unavailable(monkeypatch) -> None:
    def boom(*a, **k):
        raise OSError("no ps")

    monkeypatch.setattr(steam.subprocess, "run", boom)
    assert steam.steam_running() is False
