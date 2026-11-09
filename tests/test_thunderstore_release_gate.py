import hashlib
import json
import pytest
import yaml
from pathlib import Path
from thunderstore_release_gate import (
    PACKAGE_PATHS,
    affects_package,
    main,
    blocking_problems,
    path_matches,
    previous_stable_tag,
    release_affects_package,
    release_problems,
    synchronized_versions,
    verify_checksum,
)

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/thunderstore.yml"
VERSION_LINE = '[BepInPlugin("megabonklevels.runtime", "Megabonk Level Editor", "0.2.0")] // x-release-please-version'


@pytest.mark.parametrize(
    "path",
    [
        "src/MegabonkLevels.Mod/console_log_store.cs",
        "src/MegabonkLevels.Mod/MegabonkLevels.Mod.csproj",
        "src/MegabonkLevels.Mod/Directory.Build.props",
        "thunderstore.toml",
        "pkg/README.md",
        "pkg/icon.png",
        "pkg/manifest.json",
        "pkg/NLayer.LICENSE.txt",
        "taskfiles/package.yml",
        "scripts/check_thunderstore_package.py",
        "scripts/validate_thunderstore_manifest.py",
        "scripts/thunderstore_release_gate.py",
        ".github/workflows/thunderstore.yml",
    ],
)
def test_package_inputs_are_included(path):
    assert affects_package([path])


@pytest.mark.parametrize(
    "path",
    [
        "site/src/pages/index.astro",
        "site/package.json",
        "docs/development.md",
        "docs/thunderstore.md",
        "backlog/tasks/task-056.06 - Automate.md",
        "README.md",
        "CHANGELOG.md",
        ".claude/settings.json",
        ".agents/skills/x/SKILL.md",
        "levels/thps.mblevel.json",
        "scripts/run.py",
        "tests/test_run.py",
        ".github/workflows/release-please.yml",
    ],
)
def test_unrelated_paths_are_excluded(path):
    assert not affects_package([path])


def test_one_package_path_among_unrelated_ones_is_enough():
    assert affects_package(["docs/a.md", "site/b.astro", "pkg/README.md"])


def test_no_changed_paths_affect_nothing():
    assert not affects_package([])


def test_double_star_crosses_directories_and_single_star_does_not():
    assert path_matches("src/MegabonkLevels.Mod/deep/nested/file.cs", "src/MegabonkLevels.Mod/**")
    assert path_matches("pkg/icon.png", "pkg/*")
    assert not path_matches("pkg/nested/icon.png", "pkg/*")
    assert not path_matches("src/MegabonkLevels.ModX/file.cs", "src/MegabonkLevels.Mod/**")


def test_workflow_push_paths_match_the_gate_pattern_list():
    document = yaml.safe_load(WORKFLOW.read_text())
    triggers = document.get("on", document.get(True))
    assert list(triggers["push"]["paths"]) == list(PACKAGE_PATHS)
    assert triggers["push"]["branches"] == ["main"]


def test_release_only_bumping_version_lines_does_not_affect_the_package():
    changed = {
        "thunderstore.toml": ['-versionNumber = "0.1.0"', '+versionNumber = "0.2.0"'],
        "pkg/manifest.json": ['-  "version_number": "0.1.0",', '+  "version_number": "0.2.0",'],
        "src/MegabonkLevels.Mod/MegabonkLevels.Mod.csproj": ["-    <Version>0.1.0</Version>", "+    <Version>0.2.0</Version>"],
        "src/MegabonkLevels.Mod/megabonk_levels_mod.cs": ["-" + VERSION_LINE.replace("0.2.0", "0.1.0"), "+" + VERSION_LINE],
        "pyproject.toml": ['-version = "0.1.0"', '+version = "0.2.0"'],
        "uv.lock": ['-version = "0.1.0"', '+version = "0.2.0"'],
        "CHANGELOG.md": ["+## 0.2.0"],
        ".release-please-manifest.json": ['-  ".": "0.1.0"', '+  ".": "0.2.0"'],
    }
    assert not release_affects_package(changed)


def test_release_with_a_source_change_alongside_the_version_bump_affects_the_package():
    changed = {
        "thunderstore.toml": ['-versionNumber = "0.1.0"', '+versionNumber = "0.2.0"'],
        "src/MegabonkLevels.Mod/console_log_store.cs": ["+int x;"],
    }
    assert release_affects_package(changed)


def test_a_version_file_with_a_non_version_line_changed_affects_the_package():
    changed = {
        "thunderstore.toml": ['-versionNumber = "0.1.0"', '+versionNumber = "0.2.0"', '+description = "new"'],
    }
    assert release_affects_package(changed)


def test_a_bumped_dependency_pin_in_the_manifest_affects_the_package():
    changed = {"pkg/manifest.json": ['-    "BepInEx-BepInExPack_IL2CPP-6.0.788"', '+    "BepInEx-BepInExPack_IL2CPP-6.0.900"']}
    assert release_affects_package(changed)


def test_unrelated_release_changes_do_not_affect_the_package():
    assert not release_affects_package({"site/src/a.astro": ["+x"], "docs/a.md": ["+y"]})


def test_previous_stable_tag_skips_prereleases_and_newer_tags():
    tags = ["v0.1.0", "v0.2.0-rc.1", "v0.2.0", "v0.3.0", "v0.10.0", "not-a-version"]
    assert previous_stable_tag("v0.3.0", tags) == "v0.2.0"
    assert previous_stable_tag("v0.10.0", tags) == "v0.3.0"
    assert previous_stable_tag("v0.1.0", tags) is None


def good(**overrides):
    arguments = {"event": "release", "tag": "v0.2.0", "prerelease": False, "version": "0.2.0", "published": False}
    return release_problems(**{**arguments, **overrides})


def test_a_stable_release_for_an_unpublished_version_has_no_problems():
    assert good() == []


@pytest.mark.parametrize("event", ["pull_request", "pull_request_target", "schedule", "workflow_run"])
def test_untrusted_or_build_only_events_cannot_publish(event):
    assert good(event=event)


def test_manual_dispatch_may_publish_a_tag():
    assert good(event="workflow_dispatch") == []


def test_prereleases_cannot_publish():
    assert any("prerelease" in problem for problem in good(prerelease=True))


def test_a_tag_that_differs_from_the_package_version_cannot_publish():
    assert any("v0.2.0" in problem for problem in good(version="0.3.0"))
    assert good(tag="0.2.0")
    assert good(tag="refs/heads/main")


def test_an_already_published_version_cannot_publish_again():
    assert any("already published" in problem for problem in good(published=True))


def test_an_unknown_publication_state_blocks_publishing():
    assert any("could not be determined" in problem for problem in good(published=None))


def test_an_already_published_version_is_skipped_not_failed():
    assert blocking_problems(good(published=True), "0.2.0") == []


def test_other_problems_still_block_alongside_an_already_published_version():
    assert blocking_problems(good(published=True, prerelease=True), "0.2.0")
    assert blocking_problems(good(published=None), "0.2.0")


def test_artifact_inputs_exclude_tooling_for_release_decisions():
    assert not release_affects_package({"scripts/check_thunderstore_package.py": ["+x"], ".github/workflows/thunderstore.yml": ["+x"], "taskfiles/package.yml": ["+x"]})


def write_archive(tmp_path, content=b"zip bytes", checksum=None):
    archive = tmp_path / "pythoninthegrass-Megabonk_Level_Editor-0.2.0.zip"
    archive.write_bytes(content)
    digest = checksum or hashlib.sha256(content).hexdigest()
    record = tmp_path / (archive.name + ".sha256")
    record.write_text(f"{digest}  {archive.name}\n")
    return archive, record


def test_checksum_accepts_the_recorded_archive(tmp_path):
    archive, record = write_archive(tmp_path)
    assert verify_checksum(archive, record) == []


def test_checksum_rejects_a_modified_archive(tmp_path):
    archive, record = write_archive(tmp_path)
    archive.write_bytes(b"tampered")
    assert verify_checksum(archive, record)


def test_checksum_rejects_a_record_for_another_file(tmp_path):
    archive, record = write_archive(tmp_path)
    record.write_text(record.read_text().replace(archive.name, "other.zip"))
    assert verify_checksum(archive, record)


def test_checksum_rejects_a_missing_or_malformed_record(tmp_path):
    archive, record = write_archive(tmp_path)
    record.write_text("not a checksum\n")
    assert verify_checksum(archive, record)
    record.unlink()
    assert verify_checksum(archive, record)


def test_synchronized_versions_cover_every_package_version_source():
    versions = synchronized_versions(ROOT)
    assert set(versions) == {"thunderstore", "manifest", "assembly", "plugin", "python"}
    assert len(set(versions.values())) == 1
    assert json.loads((ROOT / "pkg/manifest.json").read_text())["version_number"] == versions["manifest"]


def test_synchronized_versions_report_a_mismatch(tmp_path):
    for relative in ("thunderstore.toml", "pyproject.toml", "pkg/manifest.json", "src/MegabonkLevels.Mod/MegabonkLevels.Mod.csproj", "src/MegabonkLevels.Mod/megabonk_levels_mod.cs"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    manifest = tmp_path / "pkg/manifest.json"
    manifest.write_text(manifest.read_text().replace('"version_number": "0.1.0"', '"version_number": "9.9.9"'))
    assert len(set(synchronized_versions(tmp_path).values())) > 1


def copy_version_sources(tmp_path):
    for relative in ("thunderstore.toml", "pyproject.toml", "pkg/manifest.json", "src/MegabonkLevels.Mod/MegabonkLevels.Mod.csproj", "src/MegabonkLevels.Mod/megabonk_levels_mod.cs"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())


def test_versions_command_reads_the_given_root(tmp_path, capsys):
    copy_version_sources(tmp_path)
    assert main(["--root", str(tmp_path), "versions"]) == 0
    manifest = tmp_path / "pkg/manifest.json"
    manifest.write_text(manifest.read_text().replace('"version_number": "0.1.0"', '"version_number": "9.9.9"'))
    assert main(["--root", str(tmp_path), "versions"]) == 1
