import check_thps_preservation as p
import copy
import json
import pytest
import subprocess
import sys
from pathlib import Path


def test_shipped_warehouse_matches_preservation_baseline() -> None:
    assert p.check() == []


def test_comparison_names_every_difference() -> None:
    expected = {"level": "original\n", "derived": {"scale": 79.2}, "assets": {"mesh": "old", "texture": "old"}}
    actual = {"level": "changed\n", "derived": {"scale": 80}, "assets": {"mesh": "new", "extra": "new"}}
    differences = p.differences(expected, actual)
    assert len(differences) == 5
    for field in ("level", "derived.scale", "assets.mesh", "assets.texture", "assets.extra"):
        assert any(field in difference for difference in differences)


def test_comparison_detects_whitespace_only_drift() -> None:
    assert p.differences({"level": "{}\n"}, {"level": "{}"})


def test_inventory_hashes_bytes_and_reports_all_missing_files(tmp_path: Path) -> None:
    (tmp_path / "mesh").write_bytes(b"mesh")
    inventory = p.fingerprints(tmp_path, ["mesh", "texture", "collision"])
    assert len(inventory["mesh"]["sha256"]) == 64
    assert inventory["texture"] is None
    assert inventory["collision"] is None
    (tmp_path / "mesh").write_bytes(b"Mesh")
    assert p.fingerprints(tmp_path, ["mesh"])["mesh"] != inventory["mesh"]


def test_required_pack_inventory_allows_additive_assets_but_not_removed_legacy_asset() -> None:
    manifest = {"id": "thps", "version": "2.0.21", "assets": ["Warehouse", "NewRamp"]}
    assert p.pack_inventory(manifest, ["bundle:thps/Warehouse", "bundle:thps/04_Superman"]) == {
        "bundle:thps/Warehouse": True, "bundle:thps/04_Superman": "AudioClip"
    }
    manifest["assets"].remove("Warehouse")
    assert p.pack_inventory(manifest, ["bundle:thps/Warehouse"])["bundle:thps/Warehouse"] is False


def test_check_compares_shipped_and_generated_levels_independently(monkeypatch) -> None:
    baseline = {"level": "original\n", "derived": {}, "assets": {}}
    actual = copy.deepcopy(baseline)
    actual["level"] = "edited\n"
    monkeypatch.setattr(p, "snapshot", lambda *args: actual)
    monkeypatch.setattr(p, "regenerate", lambda: "regenerated\n")
    monkeypatch.setattr(p, "read_baseline", lambda: baseline)
    differences = p.check()
    assert any("shipped.level" in d for d in differences)
    assert any("generated.level" in d for d in differences)


def test_cli_check_does_not_modify_the_shipped_level() -> None:
    before = p.LEVEL_PATH.read_bytes()
    result = subprocess.run([sys.executable, str(p.__file__)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert p.LEVEL_PATH.read_bytes() == before
    baseline = json.loads(p.BASELINE_PATH.read_text())
    assert baseline["level"].encode() == before


def test_check_reports_assets_even_when_generator_inputs_are_missing(monkeypatch) -> None:
    baseline = {"level": "{}\n", "assets": {"mesh": {"sha256": "old"}, "texture": {"sha256": "old"}}}
    monkeypatch.setattr(p, "read_baseline", lambda: baseline)
    monkeypatch.setattr(p, "legacy_paths", lambda: [])
    monkeypatch.setattr(p, "fingerprints", lambda *args: {"mesh": None, "texture": None})

    def missing_snapshot(*args):
        raise FileNotFoundError("warehouse.obj")

    def failed_generator():
        raise subprocess.CalledProcessError(1, "generator", stderr="missing warehouse.obj")

    monkeypatch.setattr(p, "snapshot", missing_snapshot)
    monkeypatch.setattr(p, "regenerate", failed_generator)
    differences = "\n".join(p.check())
    for field in ("assets.mesh", "assets.texture", "generated.level", "warehouse.obj"):
        assert field in differences


@pytest.mark.parametrize("missing,generated", [(True, "original"), (False, "changed")])
def test_refresh_refuses_missing_assets_or_generator_drift(tmp_path, monkeypatch, missing, generated) -> None:
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text("do not overwrite")
    monkeypatch.setattr(p, "BASELINE_PATH", baseline_path)
    monkeypatch.setattr(sys, "argv", ["check", "--refresh"])
    monkeypatch.setattr(p, "snapshot", lambda *args: {"level": "original", "assets": {"mesh": None if missing else {"sha256": "hash"}}})
    monkeypatch.setattr(p, "regenerate", lambda: generated)
    with pytest.raises(SystemExit) as error:
        p.main()
    assert error.value.code == 2
    assert baseline_path.read_text() == "do not overwrite"
