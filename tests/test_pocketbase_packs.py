"""Pack hosting in the PocketBase service: uploads, manifest validation, id ownership and zip downloads."""

import io
import json
import os
import pytest
import uuid
import zipfile
from pathlib import Path
from test_pocketbase_service import (  # noqa: F401 (the fixtures are used by name)
    admin,
    admin_token,
    alice,
    api,
    bob,
    error_text,
    free_port,
    make_user,
    owner,
    pytestmark,
    start_service,
    stop_service,
)

MAX_TOTAL_BYTES = 30 * 1024 * 1024
BUNDLE = b"UnityFS-test-bundle" * 50


def new_pack_id() -> str:
    return "tp" + uuid.uuid4().hex[:8]


def manifest_bytes(pack_id: str, **changes) -> bytes:
    manifest = {"id": pack_id, "name": "Test Pack", "author": "alice", "version": "1.0.0", "assets": ["Crate", "Barrel"]}
    for key, value in changes.items():
        if value is None:
            manifest.pop(key, None)
        else:
            manifest[key] = value
    return json.dumps(manifest).encode()


def attachments_bytes() -> bytes:
    return json.dumps({"schema": "pack-attachments/1", "assets": {}}).encode()


def upload_pack(
    api,
    user,
    pack_id: str,
    manifest: bytes | None = None,
    attachments: bytes | None = None,
    bundles: dict | None = None,
    attested: bool = True,
    fields: list | None = None,
    method: str = "POST",
    record_id: str = "",
):
    bundles = {"windows": BUNDLE} if bundles is None else bundles
    body = [("packId", pack_id), ("description", "A test pack"), *(fields or [])]
    if attested:
        body.append(("attested", "true"))
    files = [
        ("manifest", "manifest.json", manifest if manifest is not None else manifest_bytes(pack_id), "application/json"),
        ("attachments", "attachments.json", attachments if attachments is not None else attachments_bytes(), "application/json"),
    ]
    for platform, content in bundles.items():
        files.append((f"bundle{platform.title()}", pack_id, content, "application/octet-stream"))
    path = "/api/collections/packs/records" + (f"/{record_id}" if record_id else "")
    return api.multipart(method, path, body, files, user["token"])


def create_pack(api, user, pack_id: str | None = None, **kwargs) -> dict:
    status, _, body = upload_pack(api, user, pack_id or new_pack_id(), **kwargs)
    assert status == 200, body
    return body


def field_message(body, field: str) -> str:
    return json.dumps(body["data"].get(field, {})).lower()


def test_the_packs_collection_exists(api, admin):
    assert api.request("GET", "/api/collections/packs", admin)[0] == 200


def test_a_pack_upload_derives_its_metadata_from_the_manifest(api, alice):
    pack_id = new_pack_id()
    pack = create_pack(api, alice, pack_id, bundles={"windows": BUNDLE, "linux": BUNDLE * 2})
    assert pack["packId"] == pack_id
    assert (pack["version"], pack["name"], pack["assetCount"]) == ("1.0.0", "Test Pack", 2)
    assert pack["author"] == alice["id"]
    assert (pack["downloads"], pack["hidden"], pack["attested"]) == (0, False, True)
    assert (pack["sizeWindows"], pack["sizeLinux"]) == (len(BUNDLE), len(BUNDLE) * 2)


def test_a_one_platform_pack_records_a_zero_size_for_the_other(api, alice):
    pack = create_pack(api, alice, bundles={"linux": BUNDLE})
    assert (pack["sizeWindows"], pack["sizeLinux"]) == (0, len(BUNDLE))


def test_client_supplied_derived_fields_are_overridden(api, alice):
    pack_id = new_pack_id()
    pack = create_pack(api, alice, pack_id, fields=[("version", "9.9.9"), ("assetCount", "99"), ("name", "Fake")])
    assert (pack["version"], pack["assetCount"], pack["name"]) == ("1.0.0", 2, "Test Pack")


@pytest.mark.parametrize("field,value", [("downloads", "5"), ("hidden", "true"), ("author", "someone")])
def test_clients_cannot_set_server_fields(api, alice, field, value):
    status, _, _ = upload_pack(api, alice, new_pack_id(), fields=[(field, value)])
    assert status in (400, 403)


def test_anonymous_cannot_upload(api):
    assert upload_pack(api, {"token": ""}, new_pack_id())[0] in (400, 403)


def test_an_upload_without_the_attestation_is_rejected(api, alice):
    status, _, body = upload_pack(api, alice, new_pack_id(), attested=False)
    assert status in (400, 403), body


def test_an_upload_with_the_attestation_unticked_is_rejected(api, alice):
    status, _, body = upload_pack(api, alice, new_pack_id(), attested=False, fields=[("attested", "false")])
    assert status in (400, 403), body


@pytest.mark.parametrize("pack_id", ["Upper", "has space", "-leading", "a" * 65, "../escape", "dot.ted"])
def test_a_pack_id_must_be_a_safe_folder_name(api, alice, pack_id):
    status, _, body = upload_pack(api, alice, pack_id, manifest=manifest_bytes(pack_id))
    assert status == 400, body
    assert "packId" in body["data"]


INVALID_MANIFESTS = [
    ("not-json", b"{nope", "valid json"),
    ("json-array", b"[]", "object"),
    ("id-missing", lambda p: manifest_bytes(p, id=None), "id"),
    ("id-not-string", lambda p: manifest_bytes(p, id=5), "id"),
    ("id-differs", lambda p: manifest_bytes("another"), "id"),
    ("version-missing", lambda p: manifest_bytes(p, version=None), "version"),
    ("version-not-string", lambda p: manifest_bytes(p, version=1), "version"),
    ("version-blank", lambda p: manifest_bytes(p, version="  "), "version"),
    ("assets-missing", lambda p: manifest_bytes(p, assets=None), "assets"),
    ("assets-not-list", lambda p: manifest_bytes(p, assets="Crate"), "assets"),
    ("assets-item-not-string", lambda p: manifest_bytes(p, assets=["Crate", 3]), "assets"),
    ("name-not-string", lambda p: manifest_bytes(p, name=5), "name"),
]


@pytest.mark.parametrize("label,manifest,keyword", INVALID_MANIFESTS, ids=[case[0] for case in INVALID_MANIFESTS])
def test_an_invalid_manifest_is_rejected_with_a_message_on_the_manifest_field(api, alice, label, manifest, keyword):
    pack_id = new_pack_id()
    content = manifest(pack_id) if callable(manifest) else manifest
    status, _, body = upload_pack(api, alice, pack_id, manifest=content)
    assert status == 400, body
    assert keyword in field_message(body, "manifest")


def test_invalid_attachments_are_rejected_with_a_message_on_the_attachments_field(api, alice):
    status, _, body = upload_pack(api, alice, new_pack_id(), attachments=b"not json")
    assert status == 400, body
    assert "valid json" in field_message(body, "attachments")


def test_an_upload_without_any_bundle_is_rejected(api, alice):
    status, _, body = upload_pack(api, alice, new_pack_id(), bundles={})
    assert status == 400, body
    assert "bundle" in error_text(body)


def test_an_upload_without_a_manifest_is_rejected(api, alice):
    pack_id = new_pack_id()
    files = [
        ("attachments", "attachments.json", attachments_bytes(), "application/json"),
        ("bundleWindows", pack_id, BUNDLE, "application/octet-stream"),
    ]
    status, _, body = api.multipart(
        "POST", "/api/collections/packs/records", [("packId", pack_id), ("attested", "true")], files, alice["token"]
    )
    assert status == 400, body
    assert "manifest" in body["data"]


def exact_size_bundle(pack_id: str, extra: int = 0) -> bytes:
    fixed = len(manifest_bytes(pack_id)) + len(attachments_bytes())
    return b"x" * (MAX_TOTAL_BYTES - fixed + extra)


def test_an_upload_of_exactly_thirty_mebibytes_is_accepted(api, alice):
    pack_id = new_pack_id()
    pack = create_pack(api, alice, pack_id, bundles={"windows": exact_size_bundle(pack_id)})
    assert pack["sizeWindows"] > 29 * 1024 * 1024


def test_an_upload_one_byte_over_thirty_mebibytes_is_rejected_with_a_message(api, alice):
    pack_id = new_pack_id()
    status, _, body = upload_pack(api, alice, pack_id, bundles={"windows": exact_size_bundle(pack_id, 1)})
    assert status == 400, body
    assert "30 mib" in error_text(body)


def test_two_bundles_count_together_towards_the_limit(api, alice):
    pack_id = new_pack_id()
    half = exact_size_bundle(pack_id)[: MAX_TOTAL_BYTES // 2 + 1]
    status, _, body = upload_pack(api, alice, pack_id, bundles={"windows": half, "linux": half})
    assert status == 400, body
    assert "30 mib" in error_text(body)


def test_a_pack_id_belongs_to_its_first_uploader(api, alice, bob):
    pack_id = new_pack_id()
    create_pack(api, alice, pack_id)
    status, _, body = upload_pack(api, bob, pack_id, manifest=manifest_bytes(pack_id, version="2.0.0"))
    assert status in (400, 403), body
    assert "packId" in body["data"]
    assert "belongs" in field_message(body, "packId")


def test_the_owner_can_publish_a_new_version_of_their_pack(api, alice):
    pack_id = new_pack_id()
    create_pack(api, alice, pack_id)
    newer = create_pack(api, alice, pack_id, manifest=manifest_bytes(pack_id, version="1.1.0"))
    assert newer["version"] == "1.1.0"


def test_the_same_version_cannot_be_uploaded_twice(api, alice):
    pack_id = new_pack_id()
    create_pack(api, alice, pack_id)
    status, _, body = upload_pack(api, alice, pack_id)
    assert status == 400, body
    assert "version" in error_text(body)


def test_a_site_owner_can_publish_a_version_and_the_author_stays_the_first_uploader(api, alice, owner):
    pack_id = new_pack_id()
    create_pack(api, alice, pack_id)
    newer = create_pack(api, owner, pack_id, manifest=manifest_bytes(pack_id, version="1.2.0"))
    assert newer["author"] == alice["id"]


def test_anyone_can_list_visible_packs_and_hidden_ones_are_only_for_the_author_and_owners(api, admin, alice, bob, owner):
    pack = create_pack(api, alice)
    api.json("PATCH", f"/api/collections/packs/records/{pack['id']}", {"hidden": True}, owner["token"])
    url = f"/api/collections/packs/records/{pack['id']}"
    assert api.request("GET", url)[0] == 404
    assert api.request("GET", url, bob["token"])[0] == 404
    assert api.request("GET", url, alice["token"])[0] == 200
    assert api.request("GET", url, owner["token"])[0] == 200


def test_an_author_cannot_hide_or_edit_their_pack_but_can_delete_it(api, alice, bob):
    pack = create_pack(api, alice)
    url = f"/api/collections/packs/records/{pack['id']}"
    assert api.json("PATCH", url, {"hidden": True}, alice["token"])[0] in (400, 403, 404)
    assert api.json("PATCH", url, {"description": "x"}, bob["token"])[0] in (400, 403, 404)
    assert api.request("DELETE", url, bob["token"])[0] in (403, 404)
    assert api.request("DELETE", url, alice["token"])[0] == 204


def test_the_visibility_lists_are_only_shown_to_site_owners(api, alice, owner):
    pack = create_pack(api, alice)
    url = f"/api/collections/packs/records/{pack['id']}"
    api.json("PATCH", url, {"viewers": [alice["id"]]}, owner["token"])
    assert "viewers" not in api.request("GET", url, alice["token"])[2]
    assert api.request("GET", url, owner["token"])[2]["viewers"] == [alice["id"]]
    assert api.request("GET", url + "?filter=viewers.id%3D'x'", alice["token"])[0] == 400


def open_zip(content: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(content))


def test_the_download_is_a_zip_that_unpacks_into_the_level_packs_folder(api, alice):
    pack_id = new_pack_id()
    create_pack(api, alice, pack_id, bundles={"windows": BUNDLE, "linux": BUNDLE * 2})
    status, headers, body = api.request("GET", f"/api/p/{pack_id}/download?platform=windows")
    assert status == 200, body
    assert headers["Content-Type"].startswith("application/zip")
    assert f'filename="{pack_id}-1.0.0-windows.zip"' in headers["Content-Disposition"]
    with open_zip(body) as archive:
        assert sorted(archive.namelist()) == sorted(
            [f"{pack_id}/{pack_id}", f"{pack_id}/manifest.json", f"{pack_id}/attachments.json"]
        )
        assert archive.read(f"{pack_id}/{pack_id}") == BUNDLE
        assert json.loads(archive.read(f"{pack_id}/manifest.json"))["id"] == pack_id
    linux = api.request("GET", f"/api/p/{pack_id}/download?platform=linux")[2]
    with open_zip(linux) as archive:
        assert archive.read(f"{pack_id}/{pack_id}") == BUNDLE * 2


def test_the_download_defaults_to_the_latest_version_and_can_name_one(api, alice):
    pack_id = new_pack_id()
    create_pack(api, alice, pack_id, bundles={"windows": b"one"})
    create_pack(api, alice, pack_id, manifest=manifest_bytes(pack_id, version="2.0.0"), bundles={"windows": b"two"})
    latest = api.request("GET", f"/api/p/{pack_id}/download?platform=windows")[2]
    older = api.request("GET", f"/api/p/{pack_id}/download?platform=windows&version=1.0.0")[2]
    with open_zip(latest) as archive:
        assert archive.read(f"{pack_id}/{pack_id}") == b"two"
    with open_zip(older) as archive:
        assert archive.read(f"{pack_id}/{pack_id}") == b"one"


def test_a_download_counts_per_pack_record(api, admin, alice):
    pack = create_pack(api, alice)
    api.request("GET", f"/api/p/{pack['packId']}/download?platform=windows")
    api.request("GET", f"/api/p/{pack['packId']}/download?platform=windows")
    assert api.request("GET", f"/api/collections/packs/records/{pack['id']}", admin)[2]["downloads"] == 2


@pytest.mark.parametrize("query", ["", "?platform=mac", "?platform=linux", "?platform=windows&version=9.9.9"])
def test_a_download_for_a_missing_platform_or_version_is_not_found_or_rejected(api, alice, query):
    pack = create_pack(api, alice)
    status, _, _ = api.request("GET", f"/api/p/{pack['packId']}/download{query}")
    assert status in (400, 404)


def test_a_missing_pack_is_not_found(api):
    assert api.request("GET", "/api/p/nosuchpack/download?platform=windows")[0] == 404


def test_hidden_packs_are_not_downloadable_and_do_not_count(api, admin, alice, owner):
    pack = create_pack(api, alice)
    api.json("PATCH", f"/api/collections/packs/records/{pack['id']}", {"hidden": True}, owner["token"])
    assert api.request("GET", f"/api/p/{pack['packId']}/download?platform=windows")[0] == 404
    assert api.request("GET", f"/api/collections/packs/records/{pack['id']}", admin)[2]["downloads"] == 0


def test_a_download_works_when_the_data_directory_is_a_relative_path(tmp_path):
    relative = Path(os.path.relpath(tmp_path / "pb_data", os.getcwd()))
    process, client = start_service(relative, free_port(), {"PB_ADMIN_EMAILS": "owner@example.test"})
    try:
        user = make_user(client, admin_token(client), "relative")
        pack_id = new_pack_id()
        create_pack(client, user, pack_id)
        status, _, body = client.request("GET", f"/api/p/{pack_id}/download?platform=windows")
        assert status == 200, body
    finally:
        stop_service(process)
