"""Verb gating, stub classification and backup rules for scripts/swap_steam_stub.py."""

import pytest
import subprocess
import swap_steam_stub as swap
import sys

ORIGINAL = b"MZ\x90\x00" + b"valve steamworks shim " * 32
STUB_BYTES = b"MZ\x90\x00 stub " + swap.STUB_MARKER + b" and more code"
NO_ARTIFACT = "__no_such_stub_artifact__.dll"


@pytest.fixture
def plugins(tmp_path, monkeypatch):
    """A fake game layout with the shim directory, plus a built stub artifact."""
    directory = tmp_path / "Megabonk" / "Megabonk_Data" / "Plugins" / "x86_64"
    directory.mkdir(parents=True)
    artifact = tmp_path / "built" / "steam_api64.dll"
    artifact.parent.mkdir()
    artifact.write_bytes(STUB_BYTES)
    monkeypatch.setattr(swap, "STUB", artifact)
    monkeypatch.setattr(swap, "game_dir", lambda: tmp_path / "Megabonk")
    return directory


def shim_file(plugins):
    return plugins / "steam_api64.dll"


def backup_file(plugins):
    return plugins / "steam_api64.dll.steamstub.bak"


def run(monkeypatch, capsys, action):
    monkeypatch.setattr(sys, "argv", ["swap_steam_stub.py", action])
    return swap.main(), capsys.readouterr().out


def without_artifact(monkeypatch, tmp_path):
    monkeypatch.setattr(swap, "STUB", tmp_path / NO_ARTIFACT)


def test_status_reports_original_by_comparing_to_the_backup(plugins, monkeypatch, capsys, tmp_path):
    shim_file(plugins).write_bytes(ORIGINAL)
    backup_file(plugins).write_bytes(ORIGINAL)
    without_artifact(monkeypatch, tmp_path)

    code, out = run(monkeypatch, capsys, "status")

    assert code == 0
    assert "active   : ORIGINAL" in out


def test_status_calls_an_unmarked_shim_unknown_without_any_evidence(plugins, monkeypatch, capsys, tmp_path):
    shim_file(plugins).write_bytes(ORIGINAL)
    without_artifact(monkeypatch, tmp_path)

    code, out = run(monkeypatch, capsys, "status")

    assert code == 0
    assert "active   : UNKNOWN" in out
    assert "not built" in out


def test_status_recognizes_the_stub_from_its_marker_alone(plugins, monkeypatch, capsys, tmp_path):
    shim_file(plugins).write_bytes(STUB_BYTES)
    without_artifact(monkeypatch, tmp_path)

    code, out = run(monkeypatch, capsys, "status")

    assert code == 0
    assert "active   : STUB" in out


def test_status_reports_a_missing_shim_rather_than_failing(plugins, monkeypatch, capsys, tmp_path):
    without_artifact(monkeypatch, tmp_path)

    code, out = run(monkeypatch, capsys, "status")

    assert code == 0
    assert "active   : MISSING" in out
    assert "<absent>" in out


def test_restore_works_without_the_built_stub(plugins, monkeypatch, capsys, tmp_path):
    shim_file(plugins).write_bytes(STUB_BYTES)
    backup_file(plugins).write_bytes(ORIGINAL)
    without_artifact(monkeypatch, tmp_path)

    code, out = run(monkeypatch, capsys, "restore")

    assert code == 0
    assert shim_file(plugins).read_bytes() == ORIGINAL
    assert "restored ORIGINAL" in out


def test_restore_recreates_a_deleted_shim(plugins, monkeypatch, capsys):
    backup_file(plugins).write_bytes(ORIGINAL)

    code, _ = run(monkeypatch, capsys, "restore")

    assert code == 0
    assert shim_file(plugins).read_bytes() == ORIGINAL


def test_restore_without_a_backup_reports_and_fails(plugins, monkeypatch, capsys):
    shim_file(plugins).write_bytes(STUB_BYTES)

    code, out = run(monkeypatch, capsys, "restore")

    assert code == 1
    assert "no backup" in out


def test_install_still_requires_the_stub(plugins, monkeypatch, capsys, tmp_path):
    shim_file(plugins).write_bytes(ORIGINAL)
    without_artifact(monkeypatch, tmp_path)

    code, out = run(monkeypatch, capsys, "install")

    assert code == 1
    assert "task steamstub:build" in out
    assert shim_file(plugins).read_bytes() == ORIGINAL
    assert not backup_file(plugins).exists()


def test_install_backs_up_the_original_then_writes_the_stub(plugins, monkeypatch, capsys):
    shim_file(plugins).write_bytes(ORIGINAL)

    code, _ = run(monkeypatch, capsys, "install")

    assert code == 0
    assert backup_file(plugins).read_bytes() == ORIGINAL
    assert shim_file(plugins).read_bytes() == STUB_BYTES


def test_install_keeps_the_first_backup_when_the_shim_was_replaced(plugins, monkeypatch, capsys):
    shim_file(plugins).write_bytes(ORIGINAL)
    run(monkeypatch, capsys, "install")
    shim_file(plugins).write_bytes(b"hand edited shim")

    code, out = run(monkeypatch, capsys, "install")

    assert code == 0
    assert backup_file(plugins).read_bytes() == ORIGINAL
    assert shim_file(plugins).read_bytes() == STUB_BYTES
    assert "stub already installed" not in out


def test_install_on_an_installed_stub_is_a_no_op(plugins, monkeypatch, capsys):
    shim_file(plugins).write_bytes(STUB_BYTES)
    backup_file(plugins).write_bytes(ORIGINAL)

    code, out = run(monkeypatch, capsys, "install")

    assert code == 0
    assert "stub already installed" in out
    assert backup_file(plugins).read_bytes() == ORIGINAL


def test_install_refuses_to_record_a_stub_as_the_original(plugins, monkeypatch, capsys):
    shim_file(plugins).write_bytes(STUB_BYTES)

    code, out = run(monkeypatch, capsys, "install")

    assert code == 1
    assert "refusing to record the stub as the original" in out
    assert not backup_file(plugins).exists()


def test_install_without_a_shim_points_at_restore(plugins, monkeypatch, capsys):
    code, out = run(monkeypatch, capsys, "install")

    assert code == 1
    assert "restore" in out


def test_unknown_action_prints_usage(plugins, monkeypatch, capsys):
    code, out = run(monkeypatch, capsys, "frobnicate")

    assert code == 2
    assert "Usage:" in out


def test_unresolvable_game_dir_is_reported_not_raised(plugins, monkeypatch, capsys):
    def boom():
        raise subprocess.CalledProcessError(1, ["game_paths.py"], stderr="first line\nTraceback: no prefix")

    monkeypatch.setattr(swap, "game_dir", boom)

    code, out = run(monkeypatch, capsys, "status")

    assert code == 1
    assert "cannot resolve the game dir" in out
    assert "MEGABONK_GAME_DIR" in out
