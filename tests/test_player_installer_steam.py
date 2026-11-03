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
    assert steam.flatpak_override_paths(text, home=Path("/home/user")) == [Path("/home/user/games"), Path("/home/user/relative/dir")]


def test_flatpak_override_paths_ignores_other_sections_and_other_keys() -> None:
    text = "[Application]\nname=com.valvesoftware.Steam;\n[Context]\nsession-tell-filesystems=true;\nfilesystems=/ok;\n[Environment]\nfilesystems=/nope;\n"
    assert steam.flatpak_override_paths(text) == [Path("/ok")]


def test_library_roots_reads_every_client_libraryfolders(tmp_path: Path) -> None:
    client = _make_client(tmp_path / "steam", [tmp_path / "lib1", tmp_path / "lib2"])
    roots = steam.library_roots([steam.SteamClient("native", client)])
    assert [r.path for r in roots] == [tmp_path / "lib1", tmp_path / "lib2"]
    assert {r.source for r in roots} == {"client"}


def test_library_roots_marks_a_client_library_the_flatpak_is_granted(tmp_path: Path) -> None:
    library = tmp_path / "media" / "steam"
    client = _make_client(tmp_path / "steam", [library])
    (library / "steamapps").mkdir(parents=True)
    roots = steam.library_roots([steam.SteamClient("flatpak", client)], overrides=[library])
    assert [(r.path, r.source, r.granted) for r in roots] == [(library, "client", True)]


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
    monkeypatch.setattr(steam.subprocess, "run", lambda *a, **k: type("R", (), {"stdout": "123 /home/user/.local/share/Steam/ubuntu12_32/steam\n"})())
    assert steam.steam_running() is True


def test_steam_running_false_when_not_in_process_list(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(steam.subprocess, "run", lambda *a, **k: type("R", (), {"stdout": "1 python3 x.py\n"})())
    assert steam.steam_running() is False


def test_steam_running_false_when_ps_is_unavailable(monkeypatch) -> None:
    def boom(*a, **k):
        raise OSError("no ps")

    monkeypatch.setattr(steam.subprocess, "run", boom)
    assert steam.steam_running() is False


def test_client_candidates_names_every_default_location(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    candidates = steam.client_candidates(home)
    paths = [c.path for c in candidates]
    assert home / ".local" / "share" / "Steam" in paths
    assert home / ".steam" / "root" in paths
    assert home / ".steam" / "steam" in paths
    assert home / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam" in paths
    assert home / ".var" / "app" / "com.valvesoftware.Steam" / "data" / "Steam" in paths
    assert all(not c.accepted and c.reason == steam.REASON_MISSING for c in candidates)


def test_client_candidates_names_why_a_candidate_is_not_a_steam_root(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / ".local" / "share" / "Steam").mkdir(parents=True)
    candidates = {c.path: c for c in steam.client_candidates(home)}
    rejected = candidates[home / ".local" / "share" / "Steam"]
    assert not rejected.accepted
    assert rejected.reason == steam.REASON_NO_STEAMAPPS


def test_client_candidates_accepts_a_granted_root_and_flags_a_repeat(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    granted = _make_client(tmp_path / "media" / "steam", [])
    candidates = steam.client_candidates(home, granted_paths=[granted, granted])
    accepted = [c for c in candidates if c.accepted]
    assert [(c.path, c.kind) for c in accepted] == [(granted, "flatpak")]
    repeats = [c for c in candidates if c.path == granted and not c.accepted]
    assert repeats and repeats[0].reason == steam.REASON_DUPLICATE


def test_client_roots_and_client_candidates_agree(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _make_client(home / ".local" / "share" / "Steam", [])
    granted = _make_client(tmp_path / "media" / "steam", [])
    clients = steam.client_roots(home, granted_paths=[granted])
    accepted = [c for c in steam.client_candidates(home, granted_paths=[granted]) if c.accepted]
    assert [(c.kind, c.root) for c in clients] == [(c.kind, c.path) for c in accepted]


def test_library_candidates_names_an_unmounted_library_and_the_retry_path(tmp_path: Path) -> None:
    client = _make_client(tmp_path / "steam", [tmp_path / "mnt" / "games" / "SteamLibrary"])
    candidates = steam.library_candidates([steam.SteamClient("native", client)])
    rejected = [c for c in candidates if not c.accepted]
    assert [c.path for c in rejected] == [tmp_path / "mnt" / "games" / "SteamLibrary"]
    assert rejected[0].reason == steam.REASON_UNMOUNTED.format(parent=tmp_path / "mnt" / "games")


def test_library_candidates_flags_a_flatpak_library_the_sandbox_cannot_read(tmp_path: Path) -> None:
    library = tmp_path / "media" / "steam"
    (library / "steamapps").mkdir(parents=True)
    client = _make_client(tmp_path / "steam", [library])
    candidates = steam.library_candidates([steam.SteamClient("flatpak", client)])
    assert [(c.path, c.accepted, c.granted) for c in candidates] == [(library, True, False)]


def test_library_candidates_marks_a_granted_library_granted(tmp_path: Path) -> None:
    library = tmp_path / "media" / "steam"
    (library / "steamapps").mkdir(parents=True)
    client = _make_client(tmp_path / "steam", [library])
    candidates = steam.library_candidates([steam.SteamClient("flatpak", client)], overrides=[library])
    assert [(c.path, c.accepted, c.granted) for c in candidates if c.accepted] == [(library, True, True)]
    assert [c.reason for c in candidates if not c.accepted] == [steam.REASON_DUPLICATE]


def test_library_candidates_records_duplicates_against_the_first_source(tmp_path: Path) -> None:
    client = _make_client(tmp_path / "steam", [tmp_path / "lib1"])
    _make_library(tmp_path / "lib1")
    candidates = steam.library_candidates([steam.SteamClient("native", client)], overrides=[tmp_path / "lib1"])
    accepted = [c for c in candidates if c.accepted]
    assert [(c.path, c.kind) for c in accepted] == [(tmp_path / "lib1", "client")]
    repeats = [c for c in candidates if not c.accepted]
    assert [c.reason for c in repeats] == [steam.REASON_DUPLICATE]


def test_flatpak_probe_prefers_the_persisted_file_and_reports_the_source(tmp_path: Path) -> None:
    home = tmp_path / "home"
    granted = tmp_path / "data" / "steam"
    override = home / ".var" / "app" / "com.valvesoftware.Steam" / "configuration" / "flatpak" / "local-overrides" / "com.valvesoftware.Steam"
    override.parent.mkdir(parents=True)
    override.write_text(f"[Context]\nfilesystems={granted};\n")
    probe = steam.flatpak_probe(home)
    assert probe.paths == (granted,)
    assert probe.source == "file"


def test_flatpak_probe_reports_a_missing_cli(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()

    def boom(*args, **kwargs):
        raise OSError("no flatpak")

    monkeypatch.setattr(steam.subprocess, "run", boom)
    probe = steam.flatpak_probe(home)
    assert probe.paths == ()
    assert probe.source == "none"
    assert probe.cli_found is False


def test_flatpak_granted_paths_still_returns_the_probe_paths(tmp_path: Path) -> None:
    home = tmp_path / "home"
    granted = tmp_path / "data" / "steam"
    override = home / ".var" / "app" / "com.valvesoftware.Steam" / "configuration" / "flatpak" / "local-overrides" / "com.valvesoftware.Steam"
    override.parent.mkdir(parents=True)
    override.write_text(f"[Context]\nfilesystems={granted};\n")
    assert steam.flatpak_granted_paths(home) == [granted]


# ---------------------------------------------------------------- game identity


def _make_decoy(library: Path, name: str = "1000xRESIST") -> Path:
    """An unrelated Il2Cpp game: the same layout as Megabonk, nothing that names it."""
    decoy = library / "steamapps" / "common" / name
    (decoy / f"{name}_Data").mkdir(parents=True)
    (decoy / "GameAssembly.dll").write_bytes(b"MZ")
    (decoy / "UnityPlayer.dll").write_bytes(b"MZ")
    (decoy / f"{name}.exe").write_bytes(b"MZ")
    return decoy


def _make_install(library: Path, name: str, *files: str) -> Path:
    install = library / "steamapps" / "common" / name
    install.mkdir(parents=True)
    for relative in files:
        (install / relative).write_bytes(b"MZ")
    return install


def _write_manifest(library: Path, install_dir: str, app_id: str = steam.APP_ID) -> Path:
    steamapps = library / "steamapps"
    steamapps.mkdir(parents=True, exist_ok=True)
    path = steamapps / f"appmanifest_{app_id}.acf"
    path.write_text(f'"AppState"\n{{\n\t"appid"\t\t"{app_id}"\n\t"installdir"\t\t"{install_dir}"\n}}\n')
    return path


def test_find_game_dir_skips_an_unrelated_il2cpp_game_in_an_earlier_library(tmp_path: Path) -> None:
    first = _make_library(tmp_path / "lib1", with_game=False)
    _make_decoy(first)
    second = _make_library(tmp_path / "lib2")
    roots = [steam.LibraryRoot(first, "client"), steam.LibraryRoot(second, "scan")]
    assert steam.find_game_dir(roots) == second / "steamapps" / "common" / "Megabonk"


def test_find_game_dir_skips_a_decoy_sorted_before_megabonk(tmp_path: Path) -> None:
    library = _make_library(tmp_path / "lib")
    _make_decoy(library, "Heroes of Might and Magic Olden Era")
    roots = [steam.LibraryRoot(library, "client")]
    assert steam.find_game_dir(roots) == library / "steamapps" / "common" / "Megabonk"


def test_find_game_dir_none_when_the_only_il2cpp_install_is_not_megabonk(tmp_path: Path) -> None:
    library = _make_library(tmp_path / "lib", with_game=False)
    _make_decoy(library)
    assert steam.find_game_dir([steam.LibraryRoot(library, "client")]) is None


def test_find_game_dir_uses_the_app_manifest_even_with_a_decoy_ahead(tmp_path: Path) -> None:
    library = _make_library(tmp_path / "lib", with_game=False)
    _make_decoy(library, "A Decoy First")
    game = _make_install(library, "Megabonk Renamed", "Megabonk.exe")
    _write_manifest(library, "Megabonk Renamed")
    assert steam.find_game_dir([steam.LibraryRoot(library, "client")]) == game


def test_find_game_dir_refuses_an_app_manifest_whose_install_dir_is_not_megabonk(tmp_path: Path) -> None:
    library = _make_library(tmp_path / "lib", with_game=False)
    _make_decoy(library)
    _write_manifest(library, "1000xRESIST")
    assert steam.find_game_dir([steam.LibraryRoot(library, "client")]) is None


def test_find_game_dir_finds_a_renamed_install_by_its_executable(tmp_path: Path) -> None:
    library = _make_library(tmp_path / "lib", with_game=False)
    game = _make_install(library, "Megabonk (2)", "Megabonk.exe")
    assert steam.find_game_dir([steam.LibraryRoot(library, "client")]) == game


def test_find_game_dir_still_finds_the_native_build_so_it_can_be_refused(tmp_path: Path) -> None:
    library = _make_library(tmp_path / "lib", with_game=False)
    game = _make_install(library, "Megabonk", "Megabonk.x86_64")
    assert steam.find_game_dir([steam.LibraryRoot(library, "client")]) == game


def test_game_candidates_prefers_the_manifest_and_names_the_order(tmp_path: Path) -> None:
    library = _make_library(tmp_path / "lib")
    _make_decoy(library)
    candidates = steam.game_candidates([steam.LibraryRoot(library, "client")])
    assert [(c.how, c.path.name, c.accepted) for c in candidates][:2] == [
        ("name", "Megabonk", True),
        ("scan", "1000xRESIST", False),
    ]


def test_game_candidates_rejection_names_the_il2cpp_markers(tmp_path: Path) -> None:
    library = _make_library(tmp_path / "lib", with_game=False)
    _make_decoy(library)
    rejected = [c for c in steam.game_candidates([steam.LibraryRoot(library, "client")]) if not c.accepted]
    assert [c.path.name for c in rejected] == ["1000xRESIST"]
    assert rejected[0].reason == steam.REASON_NOT_MEGABONK
    assert "GameAssembly.dll" in rejected[0].reason
    assert "Megabonk_Data" in rejected[0].reason


def test_game_candidates_reports_a_manifest_candidate_and_why_it_was_refused(tmp_path: Path) -> None:
    library = _make_library(tmp_path / "lib", with_game=False)
    _write_manifest(library, "Megabonk")
    candidates = steam.game_candidates([steam.LibraryRoot(library, "client")])
    manifest_candidates = [c for c in candidates if c.how == "manifest"]
    assert [c.path.name for c in manifest_candidates] == ["Megabonk"]
    assert not manifest_candidates[0].accepted
    assert manifest_candidates[0].reason == steam.REASON_MISSING

    named = library / "steamapps" / "common" / "Megabonk"
    (named / "Megabonk_Data").mkdir(parents=True)
    candidates = [c for c in steam.game_candidates([steam.LibraryRoot(library, "client")]) if c.how == "manifest"]
    assert candidates[0].accepted


def test_game_candidates_ignores_libraries_without_a_common_directory(tmp_path: Path) -> None:
    library = tmp_path / "lib" / "steamapps"
    library.mkdir(parents=True)
    assert steam.game_candidates([steam.LibraryRoot(library.parent, "client")]) == []


# ---------------------------------------------------------------- prefix selection


def _prefix_in(library: Path, *, with_drive_c: bool = True, app_id: str = steam.APP_ID) -> Path:
    prefix = library / "steamapps" / "compatdata" / app_id / "pfx"
    if with_drive_c:
        (prefix / "drive_c").mkdir(parents=True)
    else:
        prefix.mkdir(parents=True)
    return prefix


def test_find_prefix_uses_the_prefix_beside_the_game(tmp_path: Path) -> None:
    home_library = _make_library(tmp_path / "lib1", with_game=False)
    _prefix_in(home_library)
    game_library = _make_library(tmp_path / "lib2")
    game_prefix = _prefix_in(game_library)
    game = game_library / "steamapps" / "common" / "Megabonk"
    prefix, considered = steam.find_prefix(game, [home_library, game_library])
    assert prefix == game_prefix
    assert [(c.library, c.accepted) for c in considered] == [(game_library, True), (home_library, True)]


def test_find_prefix_takes_the_only_usable_prefix_from_another_library(tmp_path: Path) -> None:
    """The SD-card layout: the game is on removable media, the active prefix is in the home library."""
    home_library = _make_library(tmp_path / "lib1", with_game=False)
    active = _prefix_in(home_library)
    game_library = _make_library(tmp_path / "lib2")
    game = game_library / "steamapps" / "common" / "Megabonk"
    prefix, considered = steam.find_prefix(game, [home_library, game_library])
    assert prefix == active
    chosen = [c for c in considered if c.accepted]
    assert [(c.path, c.library) for c in chosen] == [(active, home_library)]


def test_find_prefix_refuses_to_choose_between_two_usable_prefixes(tmp_path: Path) -> None:
    first = _make_library(tmp_path / "lib1", with_game=False)
    first_prefix = _prefix_in(first)
    second = _make_library(tmp_path / "lib2", with_game=False)
    second_prefix = _prefix_in(second)
    game = _make_library(tmp_path / "lib3") / "steamapps" / "common" / "Megabonk"
    prefix, considered = steam.find_prefix(game, [first, second])
    assert prefix is None
    assert [(c.path, c.accepted) for c in considered] == [
        (first_prefix, True),
        (second_prefix, True),
    ]


def test_find_prefix_ignores_a_prefix_without_drive_c(tmp_path: Path) -> None:
    skeleton = _make_library(tmp_path / "lib1", with_game=False)
    skeleton_prefix = _prefix_in(skeleton, with_drive_c=False)
    active = _make_library(tmp_path / "lib2", with_game=False)
    prefix = _prefix_in(active)
    game = _make_library(tmp_path / "lib3") / "steamapps" / "common" / "Megabonk"
    assert steam.find_prefix(game, [skeleton, active])[0] == prefix
    by_path = {c.path: c for c in steam.find_prefix(game, [skeleton, active])[1]}
    assert by_path[skeleton_prefix].accepted is False
    assert by_path[skeleton_prefix].reason == steam.REASON_NO_DRIVE_C


def test_find_prefix_keeps_the_games_own_unusable_prefix_so_the_warning_names_it(tmp_path: Path) -> None:
    game_library = _make_library(tmp_path / "lib")
    game = game_library / "steamapps" / "common" / "Megabonk"
    skeleton = _prefix_in(game_library, with_drive_c=False)
    assert steam.find_prefix(game, [game_library])[0] == skeleton


def test_find_prefix_none_when_no_library_has_a_prefix(tmp_path: Path) -> None:
    game_library = _make_library(tmp_path / "lib")
    game = game_library / "steamapps" / "common" / "Megabonk"
    other = _make_library(tmp_path / "lib2", with_game=False)
    prefix, considered = steam.find_prefix(game, [game_library, other])
    assert prefix is None
    assert [(c.library, c.reason) for c in considered] == [
        (game_library, steam.REASON_NO_PREFIX),
        (other, steam.REASON_NO_PREFIX),
    ]


def test_prefix_candidates_dedupes_a_library_listed_twice(tmp_path: Path) -> None:
    library = _make_library(tmp_path / "lib", with_game=False)
    prefix = _prefix_in(library)
    assert [(c.path, c.library) for c in steam.prefix_candidates([library, library])] == [(prefix, library)]
