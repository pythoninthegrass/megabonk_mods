"""Verify the exact ZIP to import locally and, after approval, publish."""

import argparse
import io
import json
import sys
import tomllib
import zipfile
from collections import Counter
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = "BepInEx/plugins/MegabonkLevels/"
BIN = "src/MegabonkLevels.Mod/bin/Release/net6.0/"


def check_package(path: Path, root: Path = ROOT) -> list[str]:
    problems = []
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as error:
        return [f"Cannot read ZIP: {error}"]
    with archive:
        config = tomllib.loads((root / "thunderstore.toml").read_text(encoding="utf-8"))
        manifest = json.loads((root / "pkg/manifest.json").read_text(encoding="utf-8"))
        sources = {
            "README.md": config["build"]["readme"],
            "icon.png": config["build"]["icon"],
            PLUGIN + "MegabonkLevels.Mod.dll": BIN + "MegabonkLevels.Mod.dll",
            PLUGIN + "NLayer.dll": BIN + "NLayer.dll",
            PLUGIN + "NLayer.LICENSE.txt": "pkg/NLayer.LICENSE.txt",
        }
        names = [entry.filename for entry in archive.infolist() if not entry.is_dir()]
        for name, count in Counter(names).items():
            if count > 1:
                problems.append(f"duplicate ZIP entry: {name}")
        expected = set(sources) | {"manifest.json"}
        for name in sorted(expected - set(names)):
            problems.append(f"missing ZIP entry: {name}")
        for name in sorted(set(names) - expected):
            problems.append(f"unexpected ZIP entry: {name}")
        for name, source in sources.items():
            if name not in names:
                continue
            try:
                if archive.read(name) != (root / source).read_bytes():
                    problems.append(f"{name} differs from {source}; rebuild and retest the ZIP")
            except OSError as error:
                problems.append(f"Cannot read source {source}: {error}")
        if "manifest.json" in names:
            try:
                actual = json.loads(archive.read("manifest.json"))
                if not isinstance(actual, dict):
                    raise ValueError("manifest must be an object")
                namespace = config["package"]["namespace"]
                identity = {"namespace": namespace, "FullName": f'{namespace}-{manifest["name"]}'}
                for key, value in identity.items():
                    if actual.pop(key, value) != value:
                        problems.append(f"ZIP manifest identity mismatch: {key}")
                if actual != manifest:
                    problems.append("ZIP manifest differs from manifest.json")
            except (ValueError, UnicodeError):
                problems.append("ZIP manifest is not valid JSON")
        if "icon.png" in names:
            try:
                with Image.open(io.BytesIO(archive.read("icon.png"))) as image:
                    if image.format != "PNG" or image.size != (256, 256):
                        problems.append("icon.png must be a 256x256 PNG")
                    image.verify()
            except (OSError, ValueError):
                problems.append("icon.png must be a valid 256x256 PNG")
        if "README.md" in names:
            try:
                text = archive.read("README.md").decode("utf-8")
                if not text.strip() or text.startswith("\ufeff"):
                    problems.append("README.md must be nonempty UTF-8 without BOM")
            except UnicodeError:
                problems.append("README.md must be UTF-8")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    problems = check_package(args.package)
    for problem in problems:
        print(problem, file=sys.stderr)
    if not problems:
        print(f"Package verified: {args.package}")
    return int(bool(problems))


if __name__ == "__main__":
    raise SystemExit(main())
