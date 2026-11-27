"""Check the kf1 pack chain: manifest, Unity builder, taskfile wiring and pack inputs."""

import glob
import json
import kf1_mountain_pass as kf1
import pytest
import shutil
import subprocess
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "unity/pack-authoring/packs/kf1/manifest.json"
BUILDER_PATH = ROOT / "unity/pack-authoring/Assets/Editor/Kf1MountainPassPack.cs"
TASKFILE = ROOT / "taskfiles/kf1.yml"
PACK_SOURCES = [
    "unity/pack-authoring/Assets/Editor/Kf1MountainPassPack.cs",
    "unity/pack-authoring/Assets/Editor/PackBuilder.cs",
    "unity/pack-authoring/Assets/ColorsVertexTint.shader",
    "unity/pack-authoring/packs/kf1/manifest.json",
    "scripts/kf1_mountain_pass.py",
    ".tools/kf1/mesh.json",
    ".tools/kf1/out/**/*.tga",
]
PACK_GENERATES = [".tools/bundles/windows/kf1", ".tools/bundles/linux/kf1"]


def write_mesh(work: Path, materials: list[dict]) -> None:
    mesh = {"meshes": [], "materials": materials, "collision": {"positions": [], "indices": []}, "perimeter": []}
    (work / "mesh.json").write_text(json.dumps(mesh))


def test_pack_textures_reports_each_referenced_texture_once(tmp_path):
    write_mesh(
        tmp_path,
        [
            {"name": "a.Tex", "texture": "out/A/T.tga", "wrapS": 10497, "wrapT": 10497},
            {"name": "b.Tex", "texture": "out/A/T.tga", "wrapS": 33071, "wrapT": 33071},
        ],
    )
    (tmp_path / "out/A").mkdir(parents=True)
    (tmp_path / "out/A/T.tga").write_bytes(b"tga")
    assert kf1.pack_textures(tmp_path) == [Path("out/A/T.tga")]


def test_pack_textures_ignores_materials_without_a_texture(tmp_path):
    write_mesh(tmp_path, [{"name": "a.Flat", "baseColor": [0.3, 0.3, 0.3, 1.0]}])
    assert kf1.pack_textures(tmp_path) == []


def test_pack_textures_names_the_material_and_texture_of_a_missing_file(tmp_path):
    write_mesh(tmp_path, [{"name": "KillingFloorStatics.TruckShader", "texture": "out/T/TruckOneCanvasDiffuseTGA.tga"}])
    with pytest.raises(ValueError) as error:
        kf1.pack_textures(tmp_path)
    message = str(error.value)
    assert "KillingFloorStatics.TruckShader" in message
    assert "out/T/TruckOneCanvasDiffuseTGA.tga" in message


def test_pack_textures_names_mesh_json_when_it_is_absent(tmp_path):
    with pytest.raises(ValueError) as error:
        kf1.pack_textures(tmp_path)
    assert "mesh.json" in str(error.value)


def test_manifest_matches_the_level_the_converter_writes():
    """The id is baked into saved levels' packs map and bundle catalogIds, so it is pinned, not derived."""
    assert kf1.PREVIEW_PACK == "kf1"
    assert kf1.PREVIEW_ASSET == "MountainPass"
    manifest = json.loads(MANIFEST_PATH.read_text())
    assert manifest["id"] == kf1.PREVIEW_PACK
    assert manifest["assets"] == [kf1.PREVIEW_ASSET]
    assert manifest["version"] == kf1.PREVIEW_PACK_VERSION


def test_the_builder_builds_the_pack_and_asset_the_level_places():
    text = BUILDER_PATH.read_text()
    assert f'const string BundleName = "{kf1.PREVIEW_PACK}";' in text
    assert f'const string AssetName = "{kf1.PREVIEW_ASSET}";' in text
    assert '"../../../.tools/kf1"' in text
    assert "Path.Combine(source, spec.texture)" in text
    assert "BuildTarget.StandaloneWindows64" in text
    assert "BuildTarget.StandaloneLinux64" in text


@pytest.fixture(autouse=True)
def _require_task():
    if shutil.which("task") is None:
        pytest.skip("task is not installed")


def _dry_run(tmp_path: Path, task_name: str = "kf1:pack", *variables: str, force: bool = True) -> str:
    taskfile = tmp_path / "Taskfile.yml"
    taskfile.write_text(
        'version: "3"\nincludes:\n'
        f'  kf1:\n    taskfile: {json.dumps(str(TASKFILE))}\n    dir: {json.dumps(str(ROOT))}\n'
        f'  pack:\n    taskfile: {json.dumps(str(ROOT / "taskfiles/pack.yml"))}\n    dir: {json.dumps(str(ROOT))}\n'
    )
    command = ["task", "--taskfile", str(taskfile), "--dry"]
    if force:
        command.append("--force")
    result = subprocess.run(
        command + [task_name, *variables],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=True,
    )
    return result.stdout + result.stderr


def test_pack_builds_both_platforms_from_the_converter_inputs(tmp_path):
    commands = _dry_run(tmp_path)
    assert "-executeMethod Kf1MountainPassPack.Build" in commands
    assert "uv run scripts/kf1_mountain_pass.py verify-pack" in commands


def test_pack_rebuilds_only_when_a_pack_input_changes():
    tasks = yaml.safe_load(TASKFILE.read_text())["tasks"]
    assert tasks["pack"]["sources"] == PACK_SOURCES
    assert tasks["pack"]["generates"] == PACK_GENERATES


def test_the_pack_builds_on_the_box_that_runs_it():
    """Both build boxes keep their own KF1 assets current, so there is no remote build leg."""
    tasks = yaml.safe_load(TASKFILE.read_text())["tasks"]
    assert set(tasks) == {"pack", "install"}
    text = TASKFILE.read_text()
    for gone in ("KF1_UNITY_HOST", "KF1_UNITY_BIN", "REMOTE_REPO", "rsync", "/usr/bin/ssh"):
        assert gone not in text, gone


def test_every_pack_source_pattern_matches_a_real_file():
    """A pattern that matches nothing makes task rebuild every run and hides a moved input."""
    if not (kf1.WORK / kf1.MESH_NAME).is_file():
        pytest.skip("prepare has not run on this box")
    for pattern in PACK_SOURCES:
        assert glob.glob(str(ROOT / pattern), recursive=True), pattern


def test_the_pack_inputs_on_disk_are_complete():
    if not (kf1.WORK / "mesh.json").exists():
        pytest.skip("prepare has not run on this box")
    textures = kf1.pack_textures(kf1.WORK)
    assert textures
    for relative in textures:
        assert (kf1.WORK / relative).is_file()
