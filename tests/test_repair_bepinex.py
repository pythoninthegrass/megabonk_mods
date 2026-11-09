import hashlib
import io
import pytest
import repair_bepinex as repair
import zipfile


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


def test_cli_dry_run_download_does_not_cache(game, pack, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(repair, "CACHE", tmp_path / "cache.zip")
    monkeypatch.setattr(repair, "download", lambda url: pack)
    assert repair.main(["--game-dir", str(game), "--download", "--dry-run"]) == 0
    assert not repair.CACHE.exists()
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
