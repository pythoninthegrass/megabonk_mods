import hashlib
import io
import pytest
import repair_bepinex as repair
import zipfile


@pytest.fixture(autouse=True)
def isolated_log(tmp_path, monkeypatch):
    monkeypatch.setattr(repair, "LOG_FILE", tmp_path / "logs/repair.log")


@pytest.fixture
def game(tmp_path, monkeypatch):
    root = tmp_path / "game with spaces"
    root.mkdir()
    for name in ("Megabonk.exe", "winhttp.dll", "doorstop_config.ini"):
        (root / name).write_bytes(b"existing")
    (root / "BepInEx/core").mkdir(parents=True)
    (root / "BepInEx/core/BepInEx.Unity.IL2CPP.dll").write_bytes(b"existing")
    monkeypatch.setattr(repair, "game_is_running", lambda: False)
    return root


@pytest.fixture
def pack(monkeypatch):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        for name, data in {
            "dotnet/coreclr.dll": b"runtime",
            "dotnet/shared/extra.dll": b"extra",
            ".doorstop_version": b"version",
            "changelog.txt": b"changes",
            "BepInEx/config/BepInEx.cfg": b"do not copy",
        }.items():
            archive.writestr("BepInExPack/" + name, data)
    body = out.getvalue()
    monkeypatch.setattr(repair, "PACK_SHA256", hashlib.sha256(body).hexdigest())
    return body


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_repairs_only_missing_files_and_parks_proxy(game, pack):
    (game / "MelonLoader").mkdir()
    (game / "version.dll").write_bytes(b"old proxy")
    (game / "UserData").mkdir()
    (game / "UserData/level.json").write_bytes(b"keep")
    before = snapshot(game)
    repair.repair(game, pack)
    assert (game / "dotnet/coreclr.dll").read_bytes() == b"runtime"
    assert (game / "dotnet/shared/extra.dll").read_bytes() == b"extra"
    assert (game / ".doorstop_version").read_bytes() == b"version"
    assert (game / "changelog.txt").read_bytes() == b"changes"
    assert (game / "version.dll.bak").read_bytes() == b"old proxy"
    assert not (game / "version.dll").exists()
    assert not (game / "BepInEx/config").exists()
    for name, data in before.items():
        if name != "version.dll":
            assert (game / name).read_bytes() == data
    after = snapshot(game)
    assert repair.repair(game, pack) == []
    assert snapshot(game) == after


def test_dry_run_changes_nothing(game, pack):
    (game / "MelonLoader").mkdir()
    (game / "version.dll").write_bytes(b"old proxy")
    before = snapshot(game)
    assert repair.repair(game, pack, dry_run=True)
    assert snapshot(game) == before
    assert not (game / "dotnet").exists()


@pytest.mark.parametrize("failure", ["checksum", "running", "backup", "conflict", "missing", "unknown-proxy"])
def test_refuses_before_any_mutation(game, pack, monkeypatch, failure):
    if failure == "checksum":
        pack += b"corrupt"
    elif failure == "running":
        monkeypatch.setattr(repair, "game_is_running", lambda: True)
    elif failure in ("backup", "unknown-proxy"):
        (game / "version.dll").write_bytes(b"proxy")
        if failure == "backup":
            (game / "MelonLoader").mkdir()
            (game / "version.dll.bak").write_bytes(b"preserve")
    elif failure == "conflict":
        (game / "dotnet").mkdir()
        (game / "dotnet/coreclr.dll").write_bytes(b"different runtime")
    else:
        (game / "winhttp.dll").unlink()
    before = snapshot(game)
    with pytest.raises(ValueError):
        repair.repair(game, pack)
    assert snapshot(game) == before


def test_refuses_symlink_destination(game, pack, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (game / "dotnet").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        repair.repair(game, pack)
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("member", ["dotnet/../escape", "dotnet/CORECLR.dll", "dotnet/link"])
def test_rejects_unsafe_archive_members(game, pack, monkeypatch, member):
    out = io.BytesIO(pack)
    with zipfile.ZipFile(out, "a") as archive:
        info = zipfile.ZipInfo("BepInExPack/" + member)
        if member.endswith("link"):
            info.external_attr = 0o120777 << 16
        archive.writestr(info, b"unsafe")
    body = out.getvalue()
    monkeypatch.setattr(repair, "PACK_SHA256", hashlib.sha256(body).hexdigest())
    with pytest.raises(ValueError):
        repair.repair(game, body)
    assert not (game / "dotnet").exists()


def test_incomplete_archive_is_refused(game, monkeypatch):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("BepInExPack/dotnet/coreclr.dll", b"incomplete")
    body = out.getvalue()
    monkeypatch.setattr(repair, "PACK_SHA256", hashlib.sha256(body).hexdigest())
    with pytest.raises(ValueError, match="missing"):
        repair.repair(game, body)


ABSOLUTE_DOORSTOP = """[General]
enabled = true
target_assembly=Z:\\other\\drive_c\\Program Files\\Megabonk\\BepInEx\\core\\BepInEx.Unity.IL2CPP.dll
redirect_output_log = false

[UnityMono]
dll_search_path_override=Z:\\other\\drive_c\\Program Files\\Megabonk\\BepInEx\\core
debug_enabled = false

[Il2Cpp]
coreclr_path = dotnet\\coreclr.dll
corlibDir = dotnet
"""


def test_rewrites_absolute_doorstop_paths_to_relative(game, pack):
    (game / "doorstop_config.ini").write_text(ABSOLUTE_DOORSTOP, encoding="utf-8")
    (game / "BepInEx/cache").mkdir()
    (game / "BepInEx/cache/chainloader_typeloader.dat").write_bytes(b"stale paths")

    actions = repair.repair(game, pack)

    text = (game / "doorstop_config.ini").read_text(encoding="utf-8")
    assert "target_assembly=BepInEx\\core\\BepInEx.Unity.IL2CPP.dll" in text
    assert "dll_search_path_override=BepInEx\\core" in text
    assert "Z:" not in text
    assert "coreclr_path = dotnet\\coreclr.dll" in text
    assert "enabled = true" in text
    assert not (game / "BepInEx/cache/chainloader_typeloader.dat").exists()
    assert (game / "doorstop_config.ini.bak").read_text(encoding="utf-8") == ABSOLUTE_DOORSTOP
    assert [a for a in actions if a.startswith("doorstop ")]


def test_relative_doorstop_config_is_left_alone(game, pack):
    relative = ABSOLUTE_DOORSTOP.replace("Z:\\other\\drive_c\\Program Files\\Megabonk\\", "")
    (game / "doorstop_config.ini").write_text(relative, encoding="utf-8")
    (game / "BepInEx/cache").mkdir()
    (game / "BepInEx/cache/chainloader_typeloader.dat").write_bytes(b"keep")

    actions = repair.repair(game, pack)

    assert (game / "doorstop_config.ini").read_text(encoding="utf-8") == relative
    assert (game / "BepInEx/cache/chainloader_typeloader.dat").read_bytes() == b"keep"
    assert not (game / "doorstop_config.ini.bak").exists()
    assert not [a for a in actions if a.startswith("doorstop ")]


def test_absolute_doorstop_pointing_elsewhere_is_left_and_reported(game, pack):
    (game / "doorstop_config.ini").write_text(
        "[General]\ntarget_assembly=C:\\shared\\BepInExPack\\core\\BepInEx.Unity.IL2CPP.dll\n", encoding="utf-8")

    actions = repair.repair(game, pack)

    assert "C:\\shared\\BepInExPack" in (game / "doorstop_config.ini").read_text(encoding="utf-8")
    assert not (game / "doorstop_config.ini.bak").exists()
    assert [a for a in actions if a.startswith("left absolute")]


def test_doorstop_rewrite_is_reported_without_writing_on_dry_run(game, pack):
    (game / "doorstop_config.ini").write_text(ABSOLUTE_DOORSTOP, encoding="utf-8")

    actions = repair.repair(game, pack, dry_run=True)

    assert [a for a in actions if a.startswith("doorstop ")]
    assert (game / "doorstop_config.ini").read_text(encoding="utf-8") == ABSOLUTE_DOORSTOP
    assert not (game / "doorstop_config.ini.bak").exists()
    assert not (game / "dotnet").exists()


def test_doorstop_rewrite_keeps_crlf_line_endings(game, pack):
    (game / "doorstop_config.ini").write_bytes(ABSOLUTE_DOORSTOP.replace("\n", "\r\n").encode("utf-8"))

    repair.repair(game, pack)

    raw = (game / "doorstop_config.ini").read_bytes()
    assert raw.count(b"\r\n") == raw.count(b"\n")
    assert b"target_assembly=BepInEx\\core\\BepInEx.Unity.IL2CPP.dll\r\n" in raw


def test_cli_dry_run_download_does_not_cache(game, pack, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(repair, "CACHE", tmp_path / "cache.zip")
    monkeypatch.setattr(repair, "download", lambda url: pack)
    assert repair.main(["--game-dir", str(game), "--download", "--dry-run"]) == 0
    assert not repair.CACHE.exists()
    assert not repair.LOG_FILE.exists()
    assert not (game / "dotnet").exists()
    assert "winhttp=n,b" in capsys.readouterr().out


def test_cli_requires_explicit_download(game, monkeypatch, tmp_path):
    monkeypatch.setattr(repair, "CACHE", tmp_path / "absent.zip")
    monkeypatch.setattr(repair, "download", lambda url: pytest.fail("unexpected network"))
    assert repair.main(["--game-dir", str(game)]) == 1


def test_cli_uses_configured_game_folder(game, pack, tmp_path, monkeypatch):
    archive = tmp_path / "pack.zip"
    archive.write_bytes(pack)
    monkeypatch.setattr(repair, "game_dir", lambda: game)
    assert repair.main(["--pack-zip", str(archive)]) == 0
    assert (game / "dotnet/coreclr.dll").exists()


def test_cli_success_is_one_line_and_details_are_logged(game, pack, tmp_path, capsys):
    archive = tmp_path / "pack.zip"
    archive.write_bytes(pack)
    args = ["--game-dir", str(game), "--pack-zip", str(archive)]
    assert repair.main(args) == 0
    output = capsys.readouterr()
    assert output.out == "BepInEx repair complete.\n"
    assert output.err == ""
    log = repair.LOG_FILE.read_text()
    assert "copy dotnet/coreclr.dll" in log
    assert str(game) in log
    assert "winhttp=n,b" in log
    assert repair.main(args) == 0
    assert capsys.readouterr().out == "BepInEx is already repaired; no changes needed.\n"
    assert repair.LOG_FILE.read_text().startswith(log)
    assert "Already repaired" in repair.LOG_FILE.read_text()


def test_cli_failure_is_logged_and_visible_on_stderr(game, tmp_path, capsys):
    archive = tmp_path / "bad.zip"
    archive.write_bytes(b"not the pinned archive")
    assert repair.main(["--game-dir", str(game), "--pack-zip", str(archive)]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "checksum mismatch" in output.err
    assert "checksum mismatch" in repair.LOG_FILE.read_text()
