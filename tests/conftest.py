"""Isolates every Python test from the developer's MEGABONK_* variables and the repo .env file."""

import importlib
import os
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Build products the repo does not carry, named as "module.ATTRIBUTE" or a repo-relative path.
# Test files carry precise skipifs over these; this net also skips a test that forgets one.
GENERATED_ARTIFACTS = (
    "build_thps_level.NODES_PATH",
    "build_thps_level.OBJ_PATH",
    "check_thps_piece_inventory.OBJ_PATH",
    "unity/pack-authoring/packs/thps/pieces.json",
    "unity/pack-authoring/Assets/Thps",
)


@pytest.fixture(autouse=True)
def isolated_megabonk_env(monkeypatch: pytest.MonkeyPatch) -> None:
    import game_paths

    for key in [key for key in os.environ if key.startswith("MEGABONK_")]:
        monkeypatch.delenv(key)
    monkeypatch.setattr(game_paths, "ENV_FILE", Path("/nonexistent/.env"))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def forbid_real_process_kill(monkeypatch: pytest.MonkeyPatch) -> None:
    def guard(pid: int, sig: int, *args: object) -> None:
        raise AssertionError(
            f"test reached os.kill({pid}, {sig}); stub it with monkeypatch.setattr(os, 'kill', ...)"
        )

    monkeypatch.setattr(os, "kill", guard)


def _artifact_path(reference: str) -> Path:
    if "/" in reference:
        return ROOT / reference
    module_name, attribute = reference.rsplit(".", 1)
    return Path(getattr(importlib.import_module(module_name), attribute))


def _absent_artifacts() -> list[Path]:
    absent = []
    for reference in GENERATED_ARTIFACTS:
        try:
            path = _artifact_path(reference)
        except (ImportError, AttributeError):
            continue
        if not path.exists():
            absent.append(path)
    return absent


def _reads_an_absent_artifact(error: BaseException, absent: list[Path]) -> str | None:
    filename = getattr(error, "filename", None)
    if not isinstance(error, FileNotFoundError) or not filename:
        return None
    target = os.path.realpath(filename)
    for path in absent:
        root = os.path.realpath(str(path))
        if target == root or target.startswith(root + os.sep):
            return str(path)
    return None


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    report = yield
    if report.outcome != "failed" or call.excinfo is None:
        return report
    absent = _absent_artifacts()
    if not absent:
        return report
    culprit = _reads_an_absent_artifact(call.excinfo.value, absent)
    if culprit is None:
        return report
    report.outcome = "skipped"
    _, lineno, _ = item.reportinfo()
    report.longrepr = (str(item.path), lineno or 0,
                       f"{culprit} is a gitignored build product; run `task thps` to produce it")
    return report
