"""Check the Squeaker pack manifest and the prefabs the Unity pack build emits."""

import json
import pytest
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "unity/pack-authoring/packs/squeaker/manifest.json"
PREFAB_DIR = ROOT / "unity/pack-authoring/Assets/Squeaker"
SQUEAKER_PREFAB = PREFAB_DIR / "Squeaker.prefab"
COOKIE_PREFAB = PREFAB_DIR / "StaleCookie.prefab"
CLIPS = ["Idle", "Run", "Jump", "Falling", "Grind"]
PARAMETERS = ["moving", "grounded", "jumping", "grinding"]

needs_prefabs = pytest.mark.skipif(
    not (SQUEAKER_PREFAB.exists() and COOKIE_PREFAB.exists()),
    reason="the Squeaker prefabs are emitted by the Unity pack build",
)


def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


def links_into_a_model(prefab: Path) -> bool:
    return re.search(r"^PrefabInstance:", prefab.read_text(), re.MULTILINE) is not None


def game_object_names(prefab: Path) -> set[str]:
    return set(re.findall(r"^  m_Name: (.+)$", prefab.read_text(), re.MULTILINE))


def test_manifest_names_the_squeaker_pack_and_both_prefabs() -> None:
    data = manifest()
    assert data["id"] == "squeaker"
    assert data["assets"] == ["Squeaker", "StaleCookie"]


@needs_prefabs
def test_squeaker_prefab_meets_the_player_renderer_requirements() -> None:
    text = SQUEAKER_PREFAB.read_text()
    assert "\nAnimator:" in text
    assert "\nSkinnedMeshRenderer:" in text
    assert {"hips", "torso"} <= game_object_names(SQUEAKER_PREFAB)


@needs_prefabs
def test_squeaker_prefab_is_fully_unpacked() -> None:
    assert not links_into_a_model(SQUEAKER_PREFAB)


@needs_prefabs
def test_squeaker_controller_holds_the_stock_clip_names() -> None:
    controller = (PREFAB_DIR / "Squeaker.controller").read_text()
    for clip in CLIPS:
        assert re.search(rf"^  m_Name: {clip}$", controller, re.MULTILINE), clip


@needs_prefabs
def test_squeaker_controller_declares_the_bool_parameters_the_player_renderer_sets() -> None:
    controller = (PREFAB_DIR / "Squeaker.controller").read_text()
    for name in PARAMETERS:
        assert re.search(rf"m_Name: {name}\n\s+m_Type: 4", controller), name


@needs_prefabs
def test_cookie_prefab_is_a_plain_mesh() -> None:
    text = COOKIE_PREFAB.read_text()
    assert "\nMeshRenderer:" in text or "\nSkinnedMeshRenderer:" in text
    assert not links_into_a_model(COOKIE_PREFAB)


@needs_prefabs
def test_built_prefabs_match_the_manifest() -> None:
    assert {path.stem for path in PREFAB_DIR.glob("*.prefab")} == set(manifest()["assets"])
