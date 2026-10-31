"""
Self-test for scripts/player_installer/vdf.py.

Parses the Valve KeyValues layout the player installer reads Steam's
libraryfolders.vdf and localconfig.vdf with.
"""

import player_installer.vdf as vdf

LIBRARYFOLDERS = """
"libraryfolders"
{
\t"0"
\t{
\t\t"path"\t\t"/home/lance/.local/share/Steam"
\t\t"label"\t\t""
\t\t"apps"
\t\t{
\t\t\t"200710"\t\t"2240977307"
\t\t\t"3405340"\t\t"522734781"
\t\t}
\t}
\t"1"
\t{
\t\t"path"\t\t"/media/sdcard/SteamLibrary"
\t\t"apps"
\t\t{
\t\t\t"3405340"\t\t"522734781"
\t\t}
\t}
}
"""

LOCALCONFIG = """
"UserStats"
{
}
"apps"
{
\t"3405340"
\t{
\t\t"LaunchOptions"\t\t"PROTON_LOG=1 %command%"
\t\t"CompatForceTool"\t\t"proton_10"
\t}
\t"538030"
\t{
\t\t"LaunchOptions"\t\t""
\t}
}
"""


def test_parse_vdf_reads_nested_sections_and_values() -> None:
    data = vdf.parse_vdf(LIBRARYFOLDERS)
    folders = data["libraryfolders"]
    assert folders["0"]["path"] == "/home/lance/.local/share/Steam"
    assert folders["1"]["path"] == "/media/sdcard/SteamLibrary"
    assert folders["0"]["apps"]["3405340"] == "522734781"


def test_parse_vdf_keeps_empty_string_value() -> None:
    data = vdf.parse_vdf(LIBRARYFOLDERS)
    assert data["libraryfolders"]["0"]["label"] == ""


def test_parse_vdf_accepts_bare_word_values() -> None:
    data = vdf.parse_vdf('"root"\n{\n\t"a"\t\t1\n\t"b"\t\ttrue\n}\n')
    assert data["root"]["a"] == "1"
    assert data["root"]["b"] == "true"


def test_parse_vdf_ignores_comments_and_blank_lines() -> None:
    data = vdf.parse_vdf('// note\n\n"root"\n{\n\t"a"\t"b"\n}\n')
    assert data == {"root": {"a": "b"}}


def test_find_all_returns_every_wildcard_hit() -> None:
    data = vdf.parse_vdf(LIBRARYFOLDERS)
    assert vdf.find_all(data, ("libraryfolders", "*", "path")) == [
        "/home/lance/.local/share/Steam",
        "/media/sdcard/SteamLibrary",
    ]


def test_find_all_missing_key_gives_empty_list() -> None:
    data = vdf.parse_vdf(LIBRARYFOLDERS)
    assert vdf.find_all(data, ("libraryfolders", "*", "nope")) == []


def test_find_all_through_a_scalar_returns_empty() -> None:
    data = vdf.parse_vdf(LIBRARYFOLDERS)
    assert vdf.find_all(data, ("libraryfolders", "0", "path", "x")) == []


def test_launch_options_for_app() -> None:
    data = vdf.parse_vdf(LOCALCONFIG)
    assert vdf.launch_options(data, "3405340") == "PROTON_LOG=1 %command%"


def test_launch_options_none_when_app_absent() -> None:
    data = vdf.parse_vdf(LOCALCONFIG)
    assert vdf.launch_options(data, "999999") is None


def test_launch_options_none_when_empty() -> None:
    data = vdf.parse_vdf(LOCALCONFIG)
    assert vdf.launch_options(data, "538030") is None


def test_compat_force_tool_for_app() -> None:
    data = vdf.parse_vdf(LOCALCONFIG)
    assert vdf.compat_force_tool(data, "3405340") == "proton_10"
    assert vdf.compat_force_tool(data, "538030") is None


def test_launch_options_searched_under_steam_apps_and_top_level_apps() -> None:
    data = vdf.parse_vdf('"Steam"\n{\n\t"apps"\n\t{\n\t\t"7"\n\t\t{\n\t\t\t"LaunchOptions"\t\t"x %command%"\n\t\t}\n\t}\n}\n')
    assert vdf.launch_options(data, "7") == "x %command%"


def test_parse_vdf_raises_on_unbalanced_brace() -> None:
    try:
        vdf.parse_vdf('"root"\n{\n\t"a"\t"b"\n')
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError on unbalanced braces")
