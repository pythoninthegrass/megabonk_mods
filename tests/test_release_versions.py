import json
import pytest
import re
import shutil
import subprocess
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = "src/MegabonkLevels.Mod/megabonk_levels_mod.cs"
PROJECT = "src/MegabonkLevels.Mod/MegabonkLevels.Mod.csproj"
UPSTREAM = ROOT / ".tools/release-please/node_modules/release-please"


def product_versions(root=ROOT):
    python = tomllib.loads((root / "pyproject.toml").read_text())
    lock = tomllib.loads((root / "uv.lock").read_text())
    project = ET.parse(root / PROJECT).getroot()
    plugin = re.search(r'BepInPlugin\("megabonklevels.runtime", "[^"]+", "([^"]+)"\)', (root / PLUGIN).read_text())
    package = tomllib.loads((root / "thunderstore.toml").read_text())
    npm = json.loads((root / "site/package.json").read_text())
    npm_lock = json.loads((root / "site/package-lock.json").read_text())
    return {
        "python": python["project"]["version"],
        "uv": next(p["version"] for p in lock["package"] if p["name"] == python["project"]["name"]),
        "assembly": project.findtext("PropertyGroup/Version"),
        "plugin": plugin[1],
        "thunderstore": package["package"]["versionNumber"],
        "manifest": json.loads((root / "pkg/manifest.json").read_text())["version_number"],
        "node": npm.get("version"),
        "npm lock": npm_lock.get("version"),
        "npm root": npm_lock["packages"][""].get("version"),
    }


def test_all_product_versions_match_release_manifest():
    version = json.loads((ROOT / ".release-please-manifest.json").read_text())["."]
    assert product_versions() == dict.fromkeys(product_versions(), version)


def test_one_root_release_keeps_languages_together():
    config = json.loads((ROOT / "release-please-config.json").read_text())
    assert set(config["packages"]) == {"."}
    package = config["packages"]["."]
    assert package["release-type"] == "python"
    assert package["include-component-in-tag"] is False
    if "release-as" in package:
        assert package["release-as"] == json.loads((ROOT / ".release-please-manifest.json").read_text())["."]


def test_extra_files_target_product_fields_not_dependencies():
    package = json.loads((ROOT / "release-please-config.json").read_text())["packages"]["."]
    entries = {(e["type"], e["path"], e.get("jsonpath", e.get("xpath"))) for e in package["extra-files"]}
    assert entries == {
        ("toml", "uv.lock", '$.package[?(@.name=="megabonk-mods" || @.name.value=="megabonk-mods")].version'),
        ("xml", PROJECT, "/Project/PropertyGroup/Version"),
        ("generic", PLUGIN, None),
        ("toml", "thunderstore.toml", "$.package.versionNumber"),
        ("json", "pkg/manifest.json", "$.version_number"),
        ("json", "site/package.json", "$.version"),
        ("json", "site/package-lock.json", "$.version"),
        ("json", "site/package-lock.json", '$.packages[""].version'),
    }
    source = (ROOT / PLUGIN).read_text()
    assert any("BepInPlugin(" in line and "x-release-please-version" in line for line in source.splitlines())


def test_workflow_uses_actions_secret_and_manifest_files():
    workflow = (ROOT / ".github/workflows/release-please.yml").read_text()
    assert "token: ${{ secrets.RELEASE_PLEASE_TOKEN }}" in workflow
    assert "config-file: release-please-config.json" in workflow
    assert "manifest-file: .release-please-manifest.json" in workflow
    assert "# RELEASE_PLEASE_TOKEN=" in (ROOT / ".env.example").read_text()


def test_renovate_covers_each_runtime_and_inline_python():
    config = json.loads((ROOT / ".github/renovate.json5").read_text())
    groups = {manager: rule["groupName"] for rule in config["packageRules"] for manager in rule["matchManagers"]}
    assert set(groups) == {"npm", "nuget", "gomod", "pep621", "pep723"}
    assert groups["pep621"] == groups["pep723"]
    pattern = config["pep723"]["managerFilePatterns"][0]
    assert re.search(pattern[1:-1], "scripts/mcp_server.py")
    assert not re.search(pattern[1:-1], ".tools/example.py")
    assert config["timezone"] == "America/Chicago"
    assert config["schedule"] == ["* 10 * * SAT"]
    assert config["lockFileMaintenance"]["schedule"] == config["schedule"]


@pytest.mark.skipif(not UPSTREAM.is_dir() or shutil.which("node") is None, reason="Install local release-please as documented to run upstream-updater integration")
def test_upstream_updaters_bump_product_versions_without_touching_dependencies(tmp_path):
    config = json.loads((ROOT / "release-please-config.json").read_text())
    files = {entry["path"] for entry in config["packages"]["."]["extra-files"]} | {"pyproject.toml", "go/go.mod"}
    for name in files:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    script = r"""
const fs = require('node:fs');
const path = require('node:path');
const base = process.argv[1];
const root = process.argv[2];
const config = JSON.parse(process.argv[3]);
const {Version} = require(path.join(base, 'build/src/version.js'));
const version = Version.parse('0.2.3');
const {PyProjectToml} = require(path.join(base, 'build/src/updaters/python/pyproject-toml.js'));
const {mergeUpdates} = require(path.join(base, 'build/src/updaters/composite.js'));
const update = (name, updater) => {
  const file = path.join(root, name);
  fs.writeFileSync(file, updater.updateContent(fs.readFileSync(file, 'utf8')));
};
const updates = [{path:'pyproject.toml', updater:new PyProjectToml({version})}];
for (const e of config.packages['.']['extra-files']) {
  const names = {json:'GenericJson',toml:'GenericToml',xml:'GenericXml',generic:'Generic'};
  const mod = e.type === 'generic' ? 'generic' : `generic-${e.type}`;
  const Updater = require(path.join(base, `build/src/updaters/${mod}.js`))[names[e.type]];
  updates.push({path:e.path, updater:e.type === 'generic' ? new Updater({version}) : new Updater(e.jsonpath ?? e.xpath, version)});
}
for (const e of mergeUpdates(updates)) update(e.path, e.updater);
"""
    subprocess.run(["node", "-e", script, str(UPSTREAM), str(tmp_path), json.dumps(config)], check=True, capture_output=True, text=True)
    assert set(product_versions(tmp_path).values()) == {"0.2.3"}
    before_lock = tomllib.loads((ROOT / "uv.lock").read_text())
    after_lock = tomllib.loads((tmp_path / "uv.lock").read_text())
    for before, after in zip(before_lock["package"], after_lock["package"], strict=True):
        if before["name"] != "megabonk-mods":
            assert before == after
    before = json.loads((ROOT / "site/package-lock.json").read_text())
    after = json.loads((tmp_path / "site/package-lock.json").read_text())
    assert {k: v for k, v in before["packages"].items() if k} == {k: v for k, v in after["packages"].items() if k}
    assert (ROOT / "go/go.mod").read_bytes() == (tmp_path / "go/go.mod").read_bytes()
    for name in ("pyproject.toml", "thunderstore.toml"):
        before = tomllib.loads((ROOT / name).read_text())
        after = tomllib.loads((tmp_path / name).read_text())
        assert before["project" if name == "pyproject.toml" else "package"]["dependencies"] == after["project" if name == "pyproject.toml" else "package"]["dependencies"]
    assert ET.parse(ROOT / PROJECT).getroot().find("ItemGroup/PackageReference").attrib == ET.parse(tmp_path / PROJECT).getroot().find("ItemGroup/PackageReference").attrib
