"""Decide whether a Thunderstore package build or publication is allowed, without uploading anything.

    uv run scripts/thunderstore_release_gate.py gate --tag v0.2.0     # package=true|false for a release
    uv run scripts/thunderstore_release_gate.py versions              # every version source agrees
    uv run scripts/thunderstore_release_gate.py guard --event release --tag v0.2.0 [--prerelease]
    uv run scripts/thunderstore_release_gate.py record <zip>          # write <zip>.sha256
    uv run scripts/thunderstore_release_gate.py checksum <zip>        # verify against <zip>.sha256
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = "src/MegabonkLevels.Mod/megabonk_levels_mod.cs"
PROJECT = "src/MegabonkLevels.Mod/MegabonkLevels.Mod.csproj"

# Paths whose content ends up in the Thunderstore ZIP.
ARTIFACT_PATHS = (
    "src/MegabonkLevels.Mod/**",
    "thunderstore.toml",
    "pkg/**",
)
# Paths that build, validate or publish the ZIP without changing its bytes.
TOOLING_PATHS = (
    "taskfiles/package.yml",
    "scripts/check_thunderstore_package.py",
    "scripts/validate_thunderstore_manifest.py",
    "scripts/asset_download.py",
    "scripts/thunderstore_release_gate.py",
    ".github/workflows/thunderstore.yml",
)
# The workflow's push `paths:` list; tests keep the two in step.
PACKAGE_PATHS = ARTIFACT_PATHS + TOOLING_PATHS

# Release Please rewrites these lines in every release, so a diff touching only them is not a package change.
VERSION_LINES = {
    "thunderstore.toml": re.compile(r"^versionNumber\s*="),
    "pkg/manifest.json": re.compile(r'^\s*"version_number"'),
    PROJECT: re.compile(r"^\s*<Version>"),
    PLUGIN: re.compile(r"x-release-please-version"),
}

STABLE_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
PUBLISHING_EVENTS = ("release", "workflow_dispatch")


def _glob_regex(pattern: str) -> re.Pattern:
    """Translate a GitHub Actions path filter: `**` crosses directories, `*` and `?` stay in one."""
    parts = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**", index):
            parts.append(".*")
            index += 2
        elif pattern[index] == "*":
            parts.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            parts.append("[^/]")
            index += 1
        else:
            parts.append(re.escape(pattern[index]))
            index += 1
    return re.compile("".join(parts) + r"\Z")


def path_matches(path: str, pattern: str) -> bool:
    return _glob_regex(pattern).match(path) is not None


def _matches_any(path: str, patterns: Iterable[str]) -> bool:
    return any(path_matches(path, pattern) for pattern in patterns)


def affects_package(paths: Iterable[str]) -> bool:
    """Whether any changed path is one the workflow's push filter builds for."""
    return any(_matches_any(path, PACKAGE_PATHS) for path in paths)


def _version_line_only(path: str, lines: list[str]) -> bool:
    marker = VERSION_LINES.get(path)
    return marker is not None and bool(lines) and all(marker.search(line[1:]) for line in lines)


def release_affects_package(changed: dict[str, list[str]]) -> bool:
    """Whether a release changed the ZIP's content; changed maps each path to its +/- diff lines.

    A shared-version bump rewrites the package version in every release, so files that changed only
    on their version line do not count.
    """
    for path, lines in changed.items():
        if _matches_any(path, ARTIFACT_PATHS) and not _version_line_only(path, lines):
            return True
    return False


def previous_stable_tag(tag: str, tags: Iterable[str]) -> str | None:
    current = STABLE_TAG.match(tag)
    if current is None:
        return None
    ceiling = tuple(map(int, current.groups()))
    older = [(tuple(map(int, match.groups())), name) for name in tags if (match := STABLE_TAG.match(name)) and tuple(map(int, match.groups())) < ceiling]
    return max(older)[1] if older else None


def release_problems(*, event: str, tag: str, prerelease: bool, version: str, published: bool | None) -> list[str]:
    """Reasons this run must not submit to Thunderstore; empty means it may."""
    problems = []
    if event not in PUBLISHING_EVENTS:
        problems.append(f"event {event!r} is build-only and cannot publish")
    if prerelease:
        problems.append("prerelease cannot publish")
    if tag != f"v{version}":
        problems.append(f"tag {tag!r} does not match the package version v{version}")
    if published is None:
        problems.append("publication state could not be determined")
    elif published:
        problems.append(f"version {version} is already published")
    return problems


def blocking_problems(problems: list[str], version: str) -> list[str]:
    """Problems that must fail the run; an already-published version only skips the upload so retries stay safe."""
    return [problem for problem in problems if problem != f"version {version} is already published"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_checksum(archive: Path, record: Path) -> list[str]:
    try:
        fields = record.read_text(encoding="utf-8").split()
    except (OSError, UnicodeError) as error:
        return [f"cannot read checksum record: {error}"]
    if len(fields) != 2 or not re.fullmatch(r"[0-9a-f]{64}", fields[0]):
        return ["checksum record is malformed"]
    if fields[1] != archive.name:
        return [f"checksum record is for {fields[1]}, not {archive.name}"]
    try:
        actual = sha256_file(archive)
    except OSError as error:
        return [f"cannot read archive: {error}"]
    return [] if actual == fields[0] else [f"{archive.name} does not match its recorded SHA-256"]


def synchronized_versions(root: Path = ROOT) -> dict[str, str]:
    package = tomllib.loads((root / "thunderstore.toml").read_text(encoding="utf-8"))
    python = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    plugin = re.search(r'BepInPlugin\("megabonklevels.runtime", "[^"]+", "([^"]+)"\)', (root / PLUGIN).read_text(encoding="utf-8"))
    return {
        "thunderstore": package["package"]["versionNumber"],
        "manifest": json.loads((root / "pkg/manifest.json").read_text(encoding="utf-8"))["version_number"],
        "assembly": ET.parse(root / PROJECT).getroot().findtext("PropertyGroup/Version"),
        "plugin": plugin[1] if plugin else "",
        "python": python["project"]["version"],
    }


def _git(*arguments: str, root: Path = ROOT) -> str:
    return subprocess.run(["git", *arguments], cwd=root, capture_output=True, text=True, check=True).stdout


def changed_between(base: str, tag: str, root: Path = ROOT) -> dict[str, list[str]]:
    changed = {}
    for path in _git("diff", "--name-only", f"{base}..{tag}", root=root).splitlines():
        diff = _git("diff", "-U0", f"{base}..{tag}", "--", path, root=root)
        changed[path] = [line for line in diff.splitlines() if line[:1] in "+-" and not line.startswith(("+++", "---"))]
    return changed


def _cmd_gate(args: argparse.Namespace) -> int:
    base = previous_stable_tag(args.tag, _git("tag", "--list").split())
    eligible = True if base is None else release_affects_package(changed_between(base, args.tag))
    print(f"package={'true' if eligible else 'false'}")
    print(f"gate: {args.tag} vs {base or 'no earlier stable tag'}: {'package build' if eligible else 'no package change'}", file=sys.stderr)
    return 0


def _cmd_versions(_: argparse.Namespace) -> int:
    versions = synchronized_versions()
    if len(set(versions.values())) == 1:
        print(f"versions synchronized: {next(iter(versions.values()))}")
        return 0
    print(f"versions differ: {versions}", file=sys.stderr)
    return 1


def _cmd_guard(args: argparse.Namespace) -> int:
    import validate_thunderstore_manifest as site

    config = tomllib.loads((ROOT / "thunderstore.toml").read_text(encoding="utf-8"))["package"]
    version = config["versionNumber"]
    published = site.package_exists(config["namespace"], config["name"], version)
    problems = release_problems(event=args.event, tag=args.tag, prerelease=args.prerelease, version=version, published=published)
    for problem in problems:
        print(problem, file=sys.stderr)
    print(f"publish={'false' if problems else 'true'}")
    return int(bool(blocking_problems(problems, version)))


def _cmd_record(args: argparse.Namespace) -> int:
    record = args.archive.with_name(args.archive.name + ".sha256")
    record.write_text(f"{sha256_file(args.archive)}  {args.archive.name}\n", encoding="utf-8")
    print(record)
    return 0


def _cmd_checksum(args: argparse.Namespace) -> int:
    problems = verify_checksum(args.archive, args.archive.with_name(args.archive.name + ".sha256"))
    for problem in problems:
        print(problem, file=sys.stderr)
    if not problems:
        print(f"checksum verified: {args.archive}")
    return int(bool(problems))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    gate = commands.add_parser("gate")
    gate.add_argument("--tag", required=True)
    gate.set_defaults(run=_cmd_gate)
    commands.add_parser("versions").set_defaults(run=_cmd_versions)
    guard = commands.add_parser("guard")
    guard.add_argument("--event", required=True)
    guard.add_argument("--tag", required=True)
    guard.add_argument("--prerelease", action="store_true")
    guard.set_defaults(run=_cmd_guard)
    for name, run in (("record", _cmd_record), ("checksum", _cmd_checksum)):
        sub = commands.add_parser(name)
        sub.add_argument("archive", type=Path)
        sub.set_defaults(run=run)
    args = parser.parse_args()
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
