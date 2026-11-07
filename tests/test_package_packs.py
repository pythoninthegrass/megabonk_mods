"""Self-test for the pack validation in scripts/package_contract/packs.py."""

import json
import package_contract.packs as packs
from pathlib import Path


def _pack_source(tmp_path: Path, pack_id: str = "thps") -> Path:
    source = tmp_path / "packsrc" / pack_id
    source.mkdir(parents=True)
    (source / pack_id).write_bytes(b"bundle bytes")
    (source / "manifest.json").write_text(
        json.dumps({"id": pack_id, "name": "THPS", "author": "user", "version": "1", "assets": ["a"]})
    )
    (source / "attachments.json").write_text('{"schema":"pack-attachments/1"}')
    return source


def test_a_pack_whose_manifest_id_mismatches_its_folder_is_refused(tmp_path: Path) -> None:
    source = _pack_source(tmp_path)
    (source / "manifest.json").write_text(json.dumps({"id": "other", "name": "n", "author": "a", "version": "1", "assets": []}))
    problems = packs.validate_pack_source(source)
    assert any("does not match" in p for p in problems)


def test_a_pack_missing_manifest_fields_is_refused(tmp_path: Path) -> None:
    source = _pack_source(tmp_path)
    (source / "manifest.json").write_text(json.dumps({"id": "thps", "name": "n"}))
    problems = packs.validate_pack_source(source)
    assert any("author" in p for p in problems) and any("assets" in p for p in problems)


def test_a_pack_with_no_bundle_is_refused(tmp_path: Path) -> None:
    source = _pack_source(tmp_path)
    (source / "thps").unlink()
    assert any("bundle" in p for p in packs.validate_pack_source(source))


def test_a_directory_that_is_not_a_pack_is_refused(tmp_path: Path) -> None:
    empty = tmp_path / "notapack"
    empty.mkdir()
    assert packs.validate_pack_source(empty) != []
