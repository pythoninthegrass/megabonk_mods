"""The install package's manifest: what the player downloads, and how the installer proves it is intact.

One JSON document at the package root lists the vendor archives and the mod files, each with a
sha256, so a truncated or tampered download is caught before anything touches the game.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

PACKAGE_SCHEMA = "megabonk-player-package/1"
VENDOR_DIR = "vendor"
HEX64 = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_TOP_LEVEL = (
    "schema",
    "platform",
    "package_id",
    "mod_version",
    "melonloader_version",
    "game_buildid",
    "generated",
    "verified_on",
    "vendors",
    "files",
)
REQUIRED_VENDOR_KEYS = ("name", "url", "sha256", "kind", "version")
REQUIRED_FILE_KEYS = ("path", "sha256", "dest")


class ManifestError(Exception):
    """The package manifest is missing, malformed, or does not describe a package this installer can use."""


@dataclass(frozen=True)
class Vendor:
    name: str
    url: str
    sha256: str
    kind: str
    version: str

    def path(self, package_root: Path | str) -> Path:
        return Path(package_root) / VENDOR_DIR / self.name


@dataclass(frozen=True)
class FileEntry:
    path: str
    sha256: str
    dest: str

    def source(self, package_root: Path | str) -> Path:
        return Path(package_root) / self.path

    def target(self, game_dir: Path | str) -> Path:
        return Path(game_dir) / self.dest


@dataclass(frozen=True)
class PackageManifest:
    schema: str
    platform: str
    package_id: str
    mod_version: str
    melonloader_version: str
    game_buildid: str
    generated: str
    verified_on: tuple
    vendors: tuple
    files: tuple

    @property
    def label(self) -> str:
        return f"MegabonkLevels {self.mod_version} (MelonLoader {self.melonloader_version})"

    def vendor(self, kind: str) -> Vendor:
        for vendor in self.vendors:
            if vendor.kind == kind:
                return vendor
        raise ManifestError(f"the package has no {kind!r} component")

    def to_dict(self) -> dict:
        return {
            "schema": self.schema,
            "platform": self.platform,
            "package_id": self.package_id,
            "mod_version": self.mod_version,
            "melonloader_version": self.melonloader_version,
            "game_buildid": self.game_buildid,
            "generated": self.generated,
            "verified_on": list(self.verified_on),
            "vendors": [asdict(vendor) for vendor in self.vendors],
            "files": [asdict(entry) for entry in self.files],
        }

    @classmethod
    def from_dict(cls, document: dict) -> PackageManifest:
        if not isinstance(document, dict):
            raise ManifestError("the package manifest is not a JSON object")
        for key in REQUIRED_TOP_LEVEL:
            if key not in document:
                raise ManifestError(f"the package manifest is missing '{key}'")
        schema = document["schema"]
        if schema != PACKAGE_SCHEMA:
            raise ManifestError(f"unrecognised package manifest schema {schema!r} (this installer understands {PACKAGE_SCHEMA!r})")
        platform = document["platform"]
        if platform not in ("linux", "windows"):
            raise ManifestError(f"unrecognised package platform {platform!r}; expected 'linux' or 'windows'")
        vendors = tuple(_vendor(entry, index) for index, entry in enumerate(document["vendors"] or ()))
        kinds = {vendor.kind for vendor in vendors}
        for required in ("melonloader", "dotnet"):
            if required not in kinds:
                raise ManifestError(f"the package manifest lists no {required!r} component")
        files = tuple(_file_entry(entry, index) for index, entry in enumerate(document["files"] or ()))
        if not files:
            raise ManifestError("the package manifest lists no files to install")
        verified = document["verified_on"]
        return cls(
            schema=schema,
            platform=platform,
            package_id=str(document["package_id"]),
            mod_version=str(document["mod_version"]),
            melonloader_version=str(document["melonloader_version"]),
            game_buildid=str(document["game_buildid"]),
            generated=str(document["generated"]),
            verified_on=tuple(verified or ()),
            vendors=vendors,
            files=files,
        )


def _require_strings(entry, keys, what: str) -> dict:
    if not isinstance(entry, dict):
        raise ManifestError(f"{what} is not a JSON object")
    for key in keys:
        if key not in entry:
            raise ManifestError(f"{what} is missing '{key}'")
    return {key: entry[key] for key in keys}


def _vendor(entry, index: int) -> Vendor:
    what = f"vendor entry {index}"
    values = _require_strings(entry, REQUIRED_VENDOR_KEYS, what)
    digest = str(values["sha256"]).lower()
    if not HEX64.match(digest):
        raise ManifestError(f"{what} ({values['name']}): sha256 is not 64 hex characters")
    extra = {key: value for key, value in entry.items() if key not in REQUIRED_VENDOR_KEYS}
    if extra:
        raise ManifestError(f"{what} has unknown field(s): {', '.join(sorted(extra))}")
    return Vendor(
        name=str(values["name"]),
        url=str(values["url"]),
        sha256=digest,
        kind=str(values["kind"]),
        version=str(values["version"]),
    )


def _file_entry(entry, index: int) -> FileEntry:
    what = f"file entry {index}"
    values = _require_strings(entry, REQUIRED_FILE_KEYS, what)
    digest = str(values["sha256"]).lower()
    if not HEX64.match(digest):
        raise ManifestError(f"{what} ({values['path']}): sha256 is not 64 hex characters")
    relative = _safe_relative(str(values["path"]), what)
    dest = _safe_relative(str(values["dest"]), what)
    return FileEntry(path=relative, sha256=digest, dest=dest)


def _safe_relative(value: str, what: str) -> str:
    normalised = value.replace("\\", "/")
    if not normalised or normalised.startswith("/") or ".." in normalised.split("/"):
        raise ManifestError(f"{what}: unsafe path {value!r}")
    return normalised


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_document(path: Path | str) -> dict:
    path = Path(path)
    if not path.is_file():
        raise ManifestError(f"no manifest.json in {path.parent} — pass --package pointing at the unzipped download")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestError(f"{path} is not valid JSON: {exc}") from exc


def load_manifest(path: Path | str) -> PackageManifest:
    return PackageManifest.from_dict(load_document(path))


def save_manifest(path: Path | str, manifest: PackageManifest) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path


def expected_files(manifest: PackageManifest) -> list[tuple[str, str]]:
    """Every (package-relative path, sha256) the package must contain, without duplicates."""
    pairs = [(f"{VENDOR_DIR}/{vendor.name}", vendor.sha256) for vendor in manifest.vendors]
    pairs += [(entry.path, entry.sha256) for entry in manifest.files]
    seen: dict[str, str] = {}
    for relative, digest in pairs:
        seen.setdefault(relative, digest)
    return sorted(seen.items())  # deterministic order, each archive checked once


def verify_package(package_root: Path | str) -> list[str]:
    """Check every file the manifest names; returns a message per problem, [] when the package is sound."""
    package_root = Path(package_root)
    manifest = load_manifest(package_root / "manifest.json")
    problems: list[str] = []
    for relative, digest in expected_files(manifest):
        target = package_root / relative
        if not target.is_file():
            problems.append(f"{relative}: missing from the package")
            continue
        actual = sha256_file(target)
        if actual != digest:
            problems.append(f"{relative}: checksum mismatch (expected {digest[:12]}…, got {actual[:12]}…)")
    return problems


def verify_vendor(manifest: PackageManifest, vendor: Vendor, package_root: Path | str) -> None:
    """Raise ManifestError unless one archive is present and matches its pin."""
    target = vendor.path(package_root)
    if not target.is_file():
        raise ManifestError(f"{vendor.name} is missing from the package")
    actual = sha256_file(target)
    if actual != vendor.sha256:
        raise ManifestError(f"{vendor.name}: checksum mismatch (expected {vendor.sha256[:12]}…, got {actual[:12]}…)")
