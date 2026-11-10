import json
import pytest
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _dry_run(tmp_path: Path, task_name: str, *variables: str) -> str:
    taskfile = tmp_path / "Taskfile.yml"
    thps = json.dumps(str(ROOT / "taskfiles/thps.yml"))
    pack = json.dumps(str(ROOT / "taskfiles/pack.yml"))
    taskfile.write_text(
        f'version: "3"\nincludes:\n  thps:\n    taskfile: {thps}\n    dir: {json.dumps(str(ROOT))}\n'
        f'  pack:\n    taskfile: {pack}\n    dir: {json.dumps(str(ROOT))}\n'
    )
    result = subprocess.run(
        ["task", "--taskfile", str(taskfile), "--dry", task_name, *variables],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=True,
    )
    return result.stdout + result.stderr


def _dry_run_install(tmp_path: Path, *variables: str) -> str:
    return _dry_run(tmp_path, "thps:install", *variables)


@pytest.fixture(autouse=True)
def _require_task():
    if shutil.which("task") is None:
        pytest.skip("task is not installed")


def test_install_copies_the_level_thumbnail_and_biome_sidecars(tmp_path):
    commands = _dry_run_install(tmp_path)
    assert 'stem="${level%.mblevel.json}"' in commands
    assert "png jpg jpeg biome.png biome.jpg biome.jpeg" in commands


def test_install_derives_sidecars_from_the_level_override(tmp_path):
    commands = _dry_run_install(tmp_path, "LEVEL=levels/other.mblevel.json")
    assert 'level="levels/other.mblevel.json"' in commands


def test_extract_defaults_to_the_thps2_tools_submodule(tmp_path):
    commands = _dry_run(tmp_path, "thps:extract", "WAREHOUSE_OBJ=missing/warehouse.obj")
    assert '--converter-dir "${THPS2_TOOLS_DIR:-tools/thps2-tools}"' in commands
