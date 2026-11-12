"""Runs the PocketBase service in pocketbase/ against a throwaway instance with a temporary data directory."""

import json
import os
import pytest
import re
import shutil
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PB_DIR = ROOT / "pocketbase"
LEVELS = ROOT / "levels"
POCKETBASE_VERSION = "0.40.6"
REAL_KILL = os.kill  # the conftest guard replaces os.kill per test; this signals only the service this file started
CODE_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{3}-[0-9A-HJKMNP-TV-Z]{3}-[0-9A-HJKMNP-TV-Z]{3}$")
ADMIN_EMAIL = "admin@example.test"
ADMIN_PASSWORD = "admin-password-for-tests"
OAUTH_ENV = {
    "PB_OAUTH_GITHUB_CLIENT_ID": "github-id",
    "PB_OAUTH_GITHUB_CLIENT_SECRET": "github-secret",
    "PB_OAUTH_GOOGLE_CLIENT_ID": "google-id",
    "PB_OAUTH_GOOGLE_CLIENT_SECRET": "google-secret",
    "PB_OAUTH_DISCORD_CLIENT_ID": "discord-id",
    "PB_OAUTH_DISCORD_CLIENT_SECRET": "discord-secret",
}
SITE_ORIGIN = "https://megabonkmod.party"
OWNER_EMAIL = "owner@example.test"


def find_pocketbase() -> Path | None:
    if configured := os.environ.get("POCKETBASE_BIN"):
        return Path(configured) if Path(configured).is_file() else None
    mise = shutil.which("mise") or str(Path.home() / ".local/bin/mise")
    if not Path(mise).exists():
        return None
    result = subprocess.run(
        [mise, "where", f"github:pocketbase/pocketbase@{POCKETBASE_VERSION}"], capture_output=True, text=True, check=False
    )
    candidate = Path(result.stdout.strip()) / "pocketbase"
    return candidate if result.returncode == 0 and candidate.is_file() else None


POCKETBASE = find_pocketbase()
INSTALL_HINT = f"PocketBase {POCKETBASE_VERSION} not installed; set POCKETBASE_BIN or run mise install github:pocketbase/pocketbase@{POCKETBASE_VERSION}"

if POCKETBASE is None and os.environ.get("POCKETBASE_REQUIRED") == "1":
    raise RuntimeError(INSTALL_HINT)

pytestmark = pytest.mark.skipif(POCKETBASE is None, reason=INSTALL_HINT)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Api:
    def __init__(self, base: str):
        self.base = base
        self.opener = urllib.request.build_opener(NoRedirect)

    def request(self, method: str, path: str, token: str | None = None, data: bytes | None = None, headers: dict | None = None):
        request = urllib.request.Request(self.base + path if path.startswith("/") else path, data=data, method=method)
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        if token:
            request.add_header("Authorization", token)
        try:
            response = self.opener.open(request, timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        raw = response.read()
        try:
            body = json.loads(raw) if raw else None
        except ValueError:
            body = raw
        return response.status if hasattr(response, "status") else response.code, response.headers, body

    def json(self, method: str, path: str, payload: dict | None = None, token: str | None = None):
        data = json.dumps(payload).encode() if payload is not None else None
        return self.request(method, path, token, data, {"Content-Type": "application/json"})

    def multipart(self, method: str, path: str, fields: list, files: list, token: str | None = None):
        boundary = uuid.uuid4().hex
        parts = []
        for name, value in fields:
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
        for name, filename, content, content_type in files:
            head = f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\nContent-Type: {content_type}\r\n\r\n'
            parts.append(head.encode() + content + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        return self.request(method, path, token, b"".join(parts), {"Content-Type": f"multipart/form-data; boundary={boundary}"})


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start_service(data_dir: Path, port: int, extra_env: dict | None = None) -> tuple[subprocess.Popen, Api]:
    env = {
        **os.environ,
        **OAUTH_ENV,
        "PB_RATE_LIMITS_ENABLED": "false",
        "PB_BIN": str(POCKETBASE),
        "PB_DATA_DIR": str(data_dir),
        "PB_HOOKS_DIR": str(PB_DIR / "pb_hooks"),
        "PB_MIGRATIONS_DIR": str(PB_DIR / "pb_migrations"),
        "PB_HTTP": f"127.0.0.1:{port}",
        **(extra_env or {}),
    }
    subprocess.run(
        [str(POCKETBASE), "superuser", "upsert", ADMIN_EMAIL, ADMIN_PASSWORD, f"--dir={data_dir}"],
        check=True,
        capture_output=True,
        env=env,
    )
    process = subprocess.Popen(["sh", str(PB_DIR / "entrypoint.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    api = Api(f"http://127.0.0.1:{port}")
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"service exited early:\n{process.stdout.read().decode()}")
        try:
            if api.request("GET", "/api/health")[0] == 200:
                return process, api
        except OSError:
            pass
        time.sleep(0.2)
    REAL_KILL(process.pid, signal.SIGTERM)
    raise RuntimeError("service did not become healthy")


def stop_service(process: subprocess.Popen) -> None:
    REAL_KILL(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        REAL_KILL(process.pid, signal.SIGKILL)


@pytest.fixture(scope="module")
def api(tmp_path_factory):
    process, client = start_service(tmp_path_factory.mktemp("pb_data"), free_port(), {"PB_ADMIN_EMAILS": OWNER_EMAIL})
    yield client
    stop_service(process)


def admin_token(client: Api) -> str:
    status, _, body = client.json(
        "POST", "/api/collections/_superusers/auth-with-password", {"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert status == 200, body
    return body["token"]


@pytest.fixture(scope="module")
def admin(api):
    return admin_token(api)


def make_user(api, admin, name: str, email: str | None = None) -> dict:
    email = email or f"{name}-{uuid.uuid4().hex[:6]}@example.test"
    status, _, user = api.json(
        "POST",
        "/api/collections/users/records",
        {"email": email, "password": "user-password-1", "passwordConfirm": "user-password-1", "name": name},
        admin,
    )
    assert status == 200, user
    status, _, session = api.json("POST", f"/api/collections/users/impersonate/{user['id']}", {"duration": 3600}, admin)
    assert status == 200, session
    return {"id": user["id"], "token": session["token"]}


@pytest.fixture(scope="module")
def alice(api, admin):
    return make_user(api, admin, "alice")


@pytest.fixture(scope="module")
def bob(api, admin):
    return make_user(api, admin, "bob")


@pytest.fixture(scope="module")
def carol(api, admin):
    return make_user(api, admin, "carol")


@pytest.fixture(scope="module")
def owner(api, admin):
    return make_user(api, admin, "owner", OWNER_EMAIL)


def level_bytes(name: str = "bramblecrown-hill", **changes) -> bytes:
    data = json.loads((LEVELS / f"{name}.mblevel.json").read_text())
    for key, value in changes.items():
        if value is DELETE:
            data.pop(key, None)
        else:
            data[key] = value
    return json.dumps(data).encode()


DELETE = object()


def image(name: str) -> bytes:
    return (LEVELS / name).read_bytes()


def upload(
    api, user, content: bytes | None = None, fields: list | None = None, files: list | None = None, method="POST", record_id=""
):
    all_files = files if files is not None else [("level", "level.mblevel.json", content or level_bytes(), "application/json")]
    if files is None:
        all_files.append(("cover", "cover.png", image("bramblecrown-hill.png"), "image/png"))
    path = "/api/collections/levels/records" + (f"/{record_id}" if record_id else "")
    return api.multipart(method, path, fields or [("description", "A test level")], all_files, user["token"])


def create_level(api, user, **kwargs) -> dict:
    status, _, body = upload(api, user, **kwargs)
    assert status == 200, body
    return body


def error_text(body) -> str:
    return json.dumps(body).lower()


def test_collections_exist(api, admin):
    for name in ("users", "levels", "likes", "reports"):
        assert api.request("GET", f"/api/collections/{name}", admin)[0] == 200, name


def test_users_use_oauth_only(api, admin):
    _, _, users = api.request("GET", "/api/collections/users", admin)
    assert users["passwordAuth"]["enabled"] is False
    assert users["oauth2"]["enabled"] is True
    providers = {provider["name"]: provider for provider in users["oauth2"]["providers"]}
    assert set(providers) == {"github", "google", "discord"}
    assert providers["github"]["clientId"] == "github-id"
    assert providers["google"]["clientId"] == "google-id"
    assert providers["discord"]["clientId"] == "discord-id"


def test_anonymous_cannot_register_a_user(api):
    status, _, _ = api.json(
        "POST",
        "/api/collections/users/records",
        {"email": "x@example.test", "password": "password-123", "passwordConfirm": "password-123"},
    )
    assert status in (400, 403)


def test_plain_level_metadata_comes_from_the_file(api, alice):
    level = create_level(api, alice)
    assert CODE_PATTERN.match(level["code"])
    assert level["title"] == "Bramblecrown Hill"
    assert level["schemaVersion"] == 4
    assert level["gameBuildId"] == "21750826"
    assert level["map"] == 1
    assert level["packs"] == {}
    assert level["author"] == alice["id"]
    assert (level["downloads"], level["likes"], level["hidden"]) == (0, 0, False)


def test_pack_level_records_pack_versions(api, alice):
    level = create_level(api, alice, content=level_bytes("thps"))
    assert level["title"] == "Warehouse"
    assert level["packs"] == {"thps": "2.0.21"}


def test_client_supplied_derived_fields_are_overridden(api, alice):
    level = create_level(api, alice, fields=[("title", "Fake"), ("schemaVersion", "2"), ("map", "9"), ("description", "x")])
    assert (level["title"], level["schemaVersion"], level["map"]) == ("Bramblecrown Hill", 4, 1)


def test_share_codes_are_unique(api, alice):
    assert create_level(api, alice)["code"] != create_level(api, alice)["code"]


@pytest.mark.parametrize("version", [1, 2, 3, 4])
def test_schema_versions_one_to_four_are_accepted(api, alice, version):
    assert create_level(api, alice, content=level_bytes(schemaVersion=version))["schemaVersion"] == version


def grid_cells(count_outside: bool = False, duplicate: bool = False) -> dict:
    cells = [{"x": 0, "z": 0, "height": 0}]
    if count_outside:
        cells.append({"x": 5, "z": 0, "height": 0})
    if duplicate:
        cells.append({"x": 0, "z": 0, "height": 1})
    return {"width": 2, "depth": 2, "cells": cells}


def scratch_level(**changes) -> bytes:
    base = {
        "schemaVersion": 4,
        "title": "Scratch",
        "baseline": "none",
        "map": 1,
        "grid": grid_cells(),
        "spawn": {"position": [0.5, 2, 0.5], "rotation": [0, 0, 0]},
        "bossSpawner": {"position": [1.5, 2, 1.5], "rotation": [0, 0, 0]},
        "edits": [],
    }
    for key, value in changes.items():
        if value is DELETE:
            base.pop(key, None)
        else:
            base[key] = value
    return json.dumps(base).encode()


REJECTED = [
    ("not-json", b"{nope", "valid json"),
    ("json-array", b"[]", "object"),
    ("version-zero", level_bytes(schemaVersion=0), "schemaversion"),
    ("version-five", level_bytes(schemaVersion=5), "schemaversion"),
    ("version-missing", level_bytes(schemaVersion=DELETE), "schemaversion"),
    ("title-missing", level_bytes(title=DELETE), "title"),
    ("title-blank", level_bytes(title="   "), "title"),
    ("edits-not-list", level_bytes(edits={}), "edits"),
    ("edit-without-optype", level_bytes(edits=[{"target": "", "payload": "{}"}]), "edits"),
    ("edit-not-object", level_bytes(edits=["x"]), "edits"),
    ("grid-cell-outside", scratch_level(grid=grid_cells(count_outside=True)), "grid"),
    ("grid-duplicate-cell", scratch_level(grid=grid_cells(duplicate=True)), "grid"),
    ("grid-zero-width", scratch_level(grid={"width": 0, "depth": 2, "cells": []}), "grid"),
    ("grid-missing-on-scratch", scratch_level(grid=DELETE), "grid"),
    ("grid-on-generated-baseline", scratch_level(baseline="generated"), "grid"),
]


@pytest.mark.parametrize(("content", "keyword"), [pytest.param(c, k, id=i) for i, c, k in REJECTED])
def test_invalid_level_files_are_rejected_with_a_clear_error(api, alice, content, keyword):
    status, _, body = upload(api, alice, content=content)
    assert status == 400
    assert keyword in error_text(body)


def test_valid_scratch_level_is_accepted(api, alice):
    assert create_level(api, alice, content=scratch_level())["title"] == "Scratch"


def test_level_file_over_one_mib_is_rejected(api, alice):
    padded = level_bytes() + b" " * (1024 * 1024)
    assert upload(api, alice, content=padded)[0] == 400


def test_cover_requires_a_png_or_jpg_within_eight_mib(api, alice):
    level_file = ("level", "level.mblevel.json", level_bytes(), "application/json")
    text_cover = [level_file, ("cover", "cover.txt", b"not an image", "text/plain")]
    huge_cover = [level_file, ("cover", "cover.png", image("bramblecrown-hill.png") + b"\0" * (8 * 1024 * 1024), "image/png")]
    assert upload(api, alice, files=text_cover)[0] == 400
    assert upload(api, alice, files=huge_cover)[0] == 400
    assert upload(api, alice, files=[level_file])[0] == 400


def test_biome_image_is_optional_and_accepted(api, alice):
    files = [
        ("level", "level.mblevel.json", level_bytes(), "application/json"),
        ("cover", "cover.png", image("bramblecrown-hill.png"), "image/png"),
        ("biome", "biome.png", image("bramblecrown-hill.biome.png"), "image/png"),
    ]
    status, _, body = upload(api, alice, files=files)
    assert status == 200 and body["biome"]


def test_description_over_2000_characters_is_rejected(api, alice):
    assert upload(api, alice, fields=[("description", "x" * 2001)])[0] == 400


def test_tags_accept_the_fixed_set_only(api, alice):
    ok = create_level(api, alice, fields=[("tags", "Speedrun"), ("tags", "Short")])
    assert ok["tags"] == ["Speedrun", "Short"]
    assert upload(api, alice, fields=[("tags", "Unknown")])[0] == 400


def test_anonymous_cannot_create_a_level(api):
    files = [
        ("level", "level.mblevel.json", level_bytes(), "application/json"),
        ("cover", "c.png", image("bramblecrown-hill.png"), "image/png"),
    ]
    assert api.multipart("POST", "/api/collections/levels/records", [], files)[0] in (400, 403)


@pytest.mark.parametrize(("field", "value"), [("code", "AAA-AAA-AAA"), ("downloads", "99"), ("likes", "99"), ("hidden", "true")])
def test_clients_cannot_set_server_fields(api, alice, field, value):
    assert upload(api, alice, fields=[(field, value)])[0] in (400, 403)
    level = create_level(api, alice)
    status, _, _ = api.multipart("PATCH", f"/api/collections/levels/records/{level['id']}", [(field, value)], [], alice["token"])
    assert status in (400, 403, 404)
    _, _, after = api.request("GET", f"/api/collections/levels/records/{level['id']}")
    assert {k: after[k] for k in ("code", "downloads", "likes", "hidden")} == {
        k: level[k] for k in ("code", "downloads", "likes", "hidden")
    }


def test_anyone_can_list_and_view_visible_levels_but_not_hidden_ones(api, admin, alice):
    visible = create_level(api, alice)
    hidden = create_level(api, alice)
    assert api.json("PATCH", f"/api/collections/levels/records/{hidden['id']}", {"hidden": True}, admin)[0] == 200
    status, _, listing = api.request("GET", "/api/collections/levels/records?perPage=200")
    ids = {item["id"] for item in listing["items"]}
    assert status == 200 and visible["id"] in ids and hidden["id"] not in ids
    assert api.request("GET", f"/api/collections/levels/records/{visible['id']}")[0] == 200
    assert api.request("GET", f"/api/collections/levels/records/{hidden['id']}")[0] == 404


def test_only_the_owner_can_update_or_delete(api, alice, bob):
    level = create_level(api, alice)
    path = f"/api/collections/levels/records/{level['id']}"
    assert api.json("PATCH", path, {"description": "stolen"}, bob["token"])[0] in (403, 404)
    assert api.request("DELETE", path, bob["token"])[0] in (403, 404)
    status, _, updated = api.json("PATCH", path, {"description": "mine"}, alice["token"])
    assert status == 200 and updated["description"] == "mine"
    assert api.request("DELETE", path, alice["token"])[0] == 204


def level_path(level: dict) -> str:
    return f"/api/collections/levels/records/{level['id']}"


def patch_level(api, level: dict, payload: dict, token: str):
    return api.json("PATCH", level_path(level), payload, token)


def can_view(api, level: dict, user: dict | None = None) -> bool:
    return api.request("GET", level_path(level), user["token"] if user else None)[0] == 200


def listed(api, level: dict, user: dict | None = None) -> bool:
    _, _, listing = api.request("GET", "/api/collections/levels/records?perPage=500", user["token"] if user else None)
    return level["id"] in {item["id"] for item in listing["items"]}


def test_only_allowlisted_emails_are_site_owners(api, admin, owner, alice):
    fetch = lambda user: api.request("GET", f"/api/collections/users/records/{user['id']}")[2]["admin"]
    assert fetch(owner) is True
    assert fetch(alice) is False


def test_a_user_cannot_promote_themselves(api, alice):
    status, _, _ = api.json("PATCH", f"/api/collections/users/records/{alice['id']}", {"admin": True}, alice["token"])
    assert status in (400, 403, 404)
    assert api.request("GET", f"/api/collections/users/records/{alice['id']}")[2]["admin"] is False


def test_a_new_account_cannot_claim_admin_through_its_create_body(api, admin):
    status, _, user = api.json(
        "POST",
        "/api/collections/users/records",
        {"email": f"sneaky-{uuid.uuid4().hex[:6]}@example.test", "password": "user-password-1", "passwordConfirm": "user-password-1", "admin": True},
        admin,
    )
    assert status == 200 and user["admin"] is False


def test_the_allowlist_is_reapplied_on_each_start(tmp_path):
    process, client = start_service(tmp_path, free_port(), {"PB_ADMIN_EMAILS": ""})
    try:
        user = make_user(client, admin_token(client), "later", "later@example.test")
        assert client.request("GET", f"/api/collections/users/records/{user['id']}")[2]["admin"] is False
    finally:
        stop_service(process)
    process, client = start_service(tmp_path, free_port(), {"PB_ADMIN_EMAILS": " Later@Example.test , other@example.test"})
    try:
        assert client.request("GET", f"/api/collections/users/records/{user['id']}")[2]["admin"] is True
    finally:
        stop_service(process)
    process, client = start_service(tmp_path, free_port(), {"PB_ADMIN_EMAILS": ""})
    try:
        assert client.request("GET", f"/api/collections/users/records/{user['id']}")[2]["admin"] is False
    finally:
        stop_service(process)


def test_the_owner_can_hide_and_unhide_any_level(api, alice, owner):
    level = create_level(api, alice)
    assert patch_level(api, level, {"hidden": True}, owner["token"])[0] == 200
    assert not listed(api, level) and not can_view(api, level)
    assert patch_level(api, level, {"hidden": False}, owner["token"])[0] == 200
    assert listed(api, level) and can_view(api, level)


def test_the_owner_can_delete_any_level_but_other_users_cannot(api, alice, bob, owner):
    level = create_level(api, alice)
    assert api.request("DELETE", level_path(level), bob["token"])[0] in (403, 404)
    assert api.request("DELETE", level_path(level), owner["token"])[0] == 204


def test_the_owner_cannot_change_server_fields(api, alice, owner):
    level = create_level(api, alice)
    for field, value in (("code", "AAA-AAA-AAA"), ("downloads", 99), ("likes", 99), ("author", owner["id"])):
        assert patch_level(api, level, {field: value}, owner["token"])[0] in (400, 403, 404), field


@pytest.mark.parametrize("field", ["hidden", "viewers", "blocked"])
def test_an_author_cannot_change_visibility_on_their_own_level(api, alice, bob, owner, field):
    level = create_level(api, alice)
    value = True if field == "hidden" else [bob["id"]]
    assert patch_level(api, level, {field: value}, alice["token"])[0] in (400, 403, 404)
    assert api.request("GET", level_path(level), owner["token"])[2][field] in (False, None, [])


def test_an_author_still_sees_their_hidden_level_but_others_do_not(api, alice, bob, owner):
    level = create_level(api, alice)
    patch_level(api, level, {"hidden": True}, owner["token"])
    assert can_view(api, level, alice) and listed(api, level, alice)
    assert not can_view(api, level, bob) and not listed(api, level, bob)
    assert can_view(api, level, owner)
    assert not can_view(api, level)


def test_a_viewer_sees_a_hidden_level_and_nobody_else_does(api, alice, bob, carol, owner):
    level = create_level(api, alice)
    assert patch_level(api, level, {"hidden": True, "viewers": [bob["id"]]}, owner["token"])[0] == 200
    assert can_view(api, level, bob) and listed(api, level, bob)
    assert not can_view(api, level, carol) and not can_view(api, level)


def test_a_blocked_user_cannot_see_a_public_level_but_others_can(api, alice, bob, carol, owner):
    level = create_level(api, alice)
    assert patch_level(api, level, {"blocked": [bob["id"]]}, owner["token"])[0] == 200
    assert not can_view(api, level, bob) and not listed(api, level, bob)
    assert can_view(api, level, carol) and can_view(api, level) and listed(api, level)


def test_the_author_still_sees_their_level_when_blocked(api, alice, owner):
    level = create_level(api, alice)
    patch_level(api, level, {"blocked": [alice["id"]]}, owner["token"])
    assert can_view(api, level, alice)


def test_visibility_lists_are_only_shown_to_the_owner(api, alice, bob, owner):
    level = create_level(api, alice)
    patch_level(api, level, {"viewers": [bob["id"]], "blocked": [bob["id"]]}, owner["token"])
    seen = api.request("GET", level_path(level), alice["token"])[2]
    assert "viewers" not in seen and "blocked" not in seen
    assert "viewers" not in api.request("GET", level_path(level))[2]
    seen = api.request("GET", level_path(level), owner["token"])[2]
    assert seen["viewers"] == [bob["id"]] and seen["blocked"] == [bob["id"]]


def list_levels(api, user: dict | None, **query) -> tuple[int, dict]:
    qs = urllib.parse.urlencode({"perPage": 500, **query})
    status, _, body = api.request("GET", f"/api/collections/levels/records?{qs}", user["token"] if user else None)
    return status, body


@pytest.mark.parametrize(
    "query",
    [
        {"filter": "blocked.id = 'x'"},
        {"filter": "viewers:length > 0"},
        {"filter": "title ~ 'a' && blocked.id ?= 'x'"},
        {"sort": "viewers"},
        {"sort": "-blocked"},
        {"expand": "viewers"},
        {"expand": "author,blocked"},
    ],
)
def test_visibility_lists_cannot_be_probed_through_query_options(api, alice, bob, owner, query):
    level = create_level(api, alice)
    patch_level(api, level, {"blocked": [bob["id"]], "viewers": [bob["id"]]}, owner["token"])
    for user in (None, alice, bob):
        assert list_levels(api, user, **query)[0] == 400, (user, query)
    assert api.request("GET", level_path(level) + "?" + urllib.parse.urlencode(query), alice["token"])[0] == 400
    assert list_levels(api, owner, **query)[0] == 200


def test_the_owner_can_filter_levels_by_their_visibility_lists(api, alice, bob, owner):
    level = create_level(api, alice)
    patch_level(api, level, {"blocked": [bob["id"]]}, owner["token"])
    status, body = list_levels(api, owner, filter=f"blocked.id ?= '{bob['id']}'")
    assert status == 200 and level["id"] in {item["id"] for item in body["items"]}


@pytest.mark.parametrize("term", ["blocked", "viewers", "it's viewers"])
def test_searching_for_the_words_blocked_or_viewers_still_works(api, term):
    escaped = term.replace("'", "\\'")
    assert list_levels(api, None, filter=f"title ~ '{escaped}' || description ~ '{escaped}'")[0] == 200


def test_downloads_follow_the_visibility_lists(api, alice, bob, carol, owner):
    level = create_level(api, alice)
    patch_level(api, level, {"hidden": True, "viewers": [bob["id"]]}, owner["token"])
    assert api.request("GET", f"/api/l/{level['code']}/download", bob["token"])[0] == 302
    assert api.request("GET", f"/api/l/{level['code']}/download", carol["token"])[0] == 404
    assert api.request("GET", f"/api/l/{level['code']}/download")[0] == 404


def test_replacing_the_file_rederives_metadata_and_keeps_the_code(api, alice):
    level = create_level(api, alice)
    files = [("level", "level.mblevel.json", level_bytes("thps"), "application/json")]
    status, _, updated = api.multipart("PATCH", f"/api/collections/levels/records/{level['id']}", [], files, alice["token"])
    assert status == 200
    assert (updated["title"], updated["packs"], updated["code"]) == ("Warehouse", {"thps": "2.0.21"}, level["code"])


def test_a_multipart_update_without_a_level_file_keeps_the_file_and_metadata(api, alice):
    level = create_level(api, alice)
    path = f"/api/collections/levels/records/{level['id']}"
    status, _, updated = api.multipart("PATCH", path, [("description", "edited")], [], alice["token"])
    assert status == 200, updated
    assert (updated["description"], updated["title"], updated["code"]) == ("edited", level["title"], level["code"])
    assert updated["level"] == level["level"]


def test_a_multipart_update_can_replace_only_the_cover(api, alice):
    level = create_level(api, alice)
    path = f"/api/collections/levels/records/{level['id']}"
    files = [("cover", "new-cover.png", image("bramblecrown-hill.png"), "image/png")]
    status, _, updated = api.multipart("PATCH", path, [], files, alice["token"])
    assert status == 200, updated
    assert updated["cover"] != level["cover"] and updated["level"] == level["level"]


def test_replacing_the_file_with_an_invalid_one_is_rejected(api, alice):
    level = create_level(api, alice)
    files = [("level", "level.mblevel.json", level_bytes(schemaVersion=9), "application/json")]
    status, _, body = api.multipart("PATCH", f"/api/collections/levels/records/{level['id']}", [], files, alice["token"])
    assert status == 400 and "schemaversion" in error_text(body)


def like_count(api, level_id: str) -> int:
    return api.request("GET", f"/api/collections/levels/records/{level_id}")[2]["likes"]


def like_records(api, admin, level_id: str) -> int:
    return api.request("GET", f"/api/collections/likes/records?filter=level='{level_id}'&perPage=1", admin)[2]["totalItems"]


def test_like_once_and_unlike_keeps_the_count_equal_to_the_records(api, admin, alice, bob):
    level = create_level(api, alice)
    body = {"level": level["id"], "user": alice["id"]}
    status, _, like = api.json("POST", "/api/collections/likes/records", body, alice["token"])
    assert status == 200 and like_count(api, level["id"]) == 1
    assert api.json("POST", "/api/collections/likes/records", body, alice["token"])[0] == 400
    assert api.json("POST", "/api/collections/likes/records", {"level": level["id"], "user": bob["id"]}, bob["token"])[0] == 200
    assert like_count(api, level["id"]) == like_records(api, admin, level["id"]) == 2
    assert api.request("DELETE", f"/api/collections/likes/records/{like['id']}", alice["token"])[0] == 204
    assert like_count(api, level["id"]) == like_records(api, admin, level["id"]) == 1


def test_cannot_like_on_behalf_of_another_user_or_delete_their_like(api, alice, bob):
    level = create_level(api, alice)
    assert api.json("POST", "/api/collections/likes/records", {"level": level["id"], "user": bob["id"]}, alice["token"])[0] in (
        400,
        403,
    )
    _, _, like = api.json("POST", "/api/collections/likes/records", {"level": level["id"], "user": bob["id"]}, bob["token"])
    assert api.request("DELETE", f"/api/collections/likes/records/{like['id']}", alice["token"])[0] in (403, 404)
    assert like_count(api, level["id"]) == 1


def test_anonymous_cannot_like(api, alice):
    level = create_level(api, alice)
    assert api.json("POST", "/api/collections/likes/records", {"level": level["id"], "user": alice["id"]})[0] in (400, 403)


def test_deleting_a_level_removes_its_likes(api, admin, alice):
    level = create_level(api, alice)
    api.json("POST", "/api/collections/likes/records", {"level": level["id"], "user": alice["id"]}, alice["token"])
    assert api.request("DELETE", f"/api/collections/levels/records/{level['id']}", alice["token"])[0] == 204
    assert like_records(api, admin, level["id"]) == 0


def test_download_counts_redirects_and_names_the_file_after_the_title(api, alice):
    level = create_level(api, alice, content=level_bytes("thps"))
    status, headers, _ = api.request("GET", f"/api/l/{level['code']}/download")
    assert status == 302
    location = headers["Location"]
    assert f"/api/files/levels/{level['id']}/" in location
    assert like_count(api, level["id"]) == 0
    assert api.request("GET", f"/api/collections/levels/records/{level['id']}")[2]["downloads"] == 1
    status, file_headers, body = api.request("GET", location)
    assert status == 200
    assert 'filename="warehouse.mblevel.json"' in file_headers["Content-Disposition"]
    assert body["title"] == "Warehouse"


def test_download_accepts_lowercase_codes_and_rejects_unknown_ones(api, alice):
    level = create_level(api, alice)
    assert api.request("GET", f"/api/l/{level['code'].lower()}/download")[0] == 302
    assert api.request("GET", "/api/l/ZZZ-ZZZ-ZZZ/download")[0] == 404


def test_hidden_levels_are_not_downloadable(api, admin, alice):
    level = create_level(api, alice)
    api.json("PATCH", f"/api/collections/levels/records/{level['id']}", {"hidden": True}, admin)
    assert api.request("GET", f"/api/l/{level['code']}/download")[0] == 404
    assert api.request("GET", f"/api/collections/levels/records/{level['id']}", admin)[2]["downloads"] == 0


def test_signed_in_users_can_report_and_only_admins_can_read_reports(api, admin, alice, bob):
    level = create_level(api, alice)
    body = {"level": level["id"], "user": bob["id"], "reason": "spam"}
    status, _, report = api.json("POST", "/api/collections/reports/records", body, bob["token"])
    assert status == 200
    assert api.json("POST", "/api/collections/reports/records", body)[0] in (400, 403)
    assert api.json("POST", "/api/collections/reports/records", {**body, "user": alice["id"]}, bob["token"])[0] in (400, 403)
    assert api.request("GET", "/api/collections/reports/records", bob["token"])[0] == 403
    assert api.request("GET", f"/api/collections/reports/records/{report['id']}", bob["token"])[0] in (403, 404)
    assert api.request("GET", f"/api/collections/reports/records/{report['id']}", admin)[0] == 200


def test_cors_allows_the_site_and_localhost_but_not_other_origins(api):
    def allowed(origin: str) -> str | None:
        return api.request(
            "OPTIONS", "/api/collections/levels/records", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
        )[1].get("Access-Control-Allow-Origin")

    assert allowed(SITE_ORIGIN) == SITE_ORIGIN
    assert allowed("http://localhost:8080") == "http://localhost:8080"
    assert allowed("https://evil.example") is None


def test_origins_can_be_overridden_from_the_environment(tmp_path):
    process, client = start_service(tmp_path, free_port(), {"PB_ORIGINS": "https://staging.example"})
    try:
        headers = {"Origin": "https://staging.example", "Access-Control-Request-Method": "GET"}
        assert client.request("OPTIONS", "/api/collections/levels/records", headers=headers)[1].get(
            "Access-Control-Allow-Origin"
        ) == ("https://staging.example")
        headers["Origin"] = SITE_ORIGIN
        assert (
            client.request("OPTIONS", "/api/collections/levels/records", headers=headers)[1].get("Access-Control-Allow-Origin")
            is None
        )
    finally:
        stop_service(process)


def oauth_client_ids(client: Api) -> dict:
    providers = client.request("GET", "/api/collections/users", admin_token(client))[2]["oauth2"]["providers"]
    return {provider["name"]: provider["clientId"] for provider in providers}


def test_oauth_credentials_are_resynced_from_the_environment_on_each_start(tmp_path):
    process, client = start_service(tmp_path, free_port(), {key: "" for key in OAUTH_ENV})
    try:
        assert oauth_client_ids(client) == {}
    finally:
        stop_service(process)
    process, client = start_service(tmp_path, free_port(), {"PB_OAUTH_GITHUB_CLIENT_ID": "rotated-id"})
    try:
        assert oauth_client_ids(client) == {"github": "rotated-id", "google": "google-id", "discord": "discord-id"}
    finally:
        stop_service(process)


def backup_settings(client: Api) -> dict:
    return client.request("GET", "/api/settings", admin_token(client))[2]["backups"]


def test_scheduled_backups_default_to_daily_keeping_seven(tmp_path):
    process, client = start_service(tmp_path, free_port())
    try:
        settings = backup_settings(client)
        assert settings["cron"] == "0 3 * * *"
        assert settings["cronMaxKeep"] == 7
    finally:
        stop_service(process)


def test_backup_schedule_and_retention_come_from_the_environment(tmp_path):
    process, client = start_service(tmp_path, free_port(), {"PB_BACKUP_CRON": "*/30 * * * *", "PB_BACKUP_KEEP": "3"})
    try:
        settings = backup_settings(client)
        assert settings["cron"] == "*/30 * * * *"
        assert settings["cronMaxKeep"] == 3
    finally:
        stop_service(process)


def test_a_backup_is_written_under_the_data_directory(tmp_path):
    process, client = start_service(tmp_path, free_port())
    try:
        assert client.request("POST", "/api/backups", admin_token(client))[0] == 204
        assert list((tmp_path / "backups").glob("*.zip"))
    finally:
        stop_service(process)


DEFAULT_RATE_LIMIT_LABELS = ["*:auth", "*:create", "/api/batch", "/api/", "/api/l/", "levels:create"]


def rate_limit_settings(client: Api) -> dict:
    return client.request("GET", "/api/settings", admin_token(client))[2]


def statuses(client: Api, path: str, count: int, headers: dict | None = None) -> list[int]:
    return [client.request("GET", path, headers=headers)[0] for _ in range(count)]


def test_rate_limits_are_on_by_default_and_trust_the_forwarded_for_header(tmp_path):
    process, client = start_service(tmp_path, free_port(), {"PB_RATE_LIMITS_ENABLED": ""})
    try:
        settings = rate_limit_settings(client)
        assert settings["rateLimits"]["enabled"] is True
        assert [rule["label"] for rule in settings["rateLimits"]["rules"]] == DEFAULT_RATE_LIMIT_LABELS
        assert settings["trustedProxy"]["headers"] == ["X-Forwarded-For"]
        assert settings["trustedProxy"]["useLeftmostIP"] is False
    finally:
        stop_service(process)


def test_default_rules_carry_their_limits(tmp_path):
    process, client = start_service(tmp_path, free_port(), {"PB_RATE_LIMITS_ENABLED": ""})
    try:
        rules = {rule["label"]: (rule["maxRequests"], rule["duration"]) for rule in rate_limit_settings(client)["rateLimits"]["rules"]}
        assert rules == {
            "*:auth": (2, 3),
            "*:create": (20, 5),
            "/api/batch": (3, 1),
            "/api/": (300, 10),
            "/api/l/": (30, 60),
            "levels:create": (10, 60),
        }
    finally:
        stop_service(process)


def test_rate_limits_can_be_switched_off(tmp_path):
    process, client = start_service(tmp_path, free_port(), {"PB_RATE_LIMITS_ENABLED": "false"})
    try:
        assert rate_limit_settings(client)["rateLimits"]["enabled"] is False
    finally:
        stop_service(process)


def test_rules_and_proxy_headers_come_from_the_environment(tmp_path):
    env = {
        "PB_RATE_LIMITS_ENABLED": "true",
        "PB_RATE_LIMIT_RULES": "/api/health 3 60, POST /api/collections/ 5 30",
        "PB_TRUSTED_PROXY_HEADERS": "X-Real-IP, CF-Connecting-IP",
    }
    process, client = start_service(tmp_path, free_port(), env)
    try:
        settings = rate_limit_settings(client)
        assert [(r["label"], r["maxRequests"], r["duration"]) for r in settings["rateLimits"]["rules"]] == [
            ("/api/health", 3, 60),
            ("POST /api/collections/", 5, 30),
        ]
        assert settings["trustedProxy"]["headers"] == ["X-Real-IP", "CF-Connecting-IP"]
    finally:
        stop_service(process)


LEVELS_LIST = "/api/collections/levels/records"


def test_a_client_over_its_limit_gets_429(tmp_path):
    process, client = start_service(tmp_path, free_port(), {"PB_RATE_LIMITS_ENABLED": "true", "PB_RATE_LIMIT_RULES": f"{LEVELS_LIST} 3 60"})
    try:
        assert statuses(client, LEVELS_LIST, 5) == [200, 200, 200, 429, 429]
    finally:
        stop_service(process)


def test_each_forwarded_client_has_its_own_budget(tmp_path):
    process, client = start_service(tmp_path, free_port(), {"PB_RATE_LIMITS_ENABLED": "true", "PB_RATE_LIMIT_RULES": f"{LEVELS_LIST} 2 60"})
    try:
        assert statuses(client, LEVELS_LIST, 3, {"X-Forwarded-For": "203.0.113.1"}) == [200, 200, 429]
        assert statuses(client, LEVELS_LIST, 2, {"X-Forwarded-For": "203.0.113.2"}) == [200, 200]
    finally:
        stop_service(process)


def test_a_specific_rule_wins_over_a_prefix_rule_whatever_their_order(tmp_path):
    for index, rules in enumerate((f"/api/ 300 10, {LEVELS_LIST} 2 60", f"{LEVELS_LIST} 2 60, /api/ 300 10")):
        process, client = start_service(tmp_path / str(index), free_port(), {"PB_RATE_LIMITS_ENABLED": "true", "PB_RATE_LIMIT_RULES": rules})
        try:
            assert statuses(client, LEVELS_LIST, 3) == [200, 200, 429], rules
            assert statuses(client, "/api/collections/users/auth-methods", 5) == [200] * 5, rules
        finally:
            stop_service(process)


def test_superusers_are_never_rate_limited(tmp_path):
    process, client = start_service(tmp_path, free_port(), {"PB_RATE_LIMITS_ENABLED": "true", "PB_RATE_LIMIT_RULES": "/api/settings 1 60"})
    try:
        token = admin_token(client)
        assert [client.request("GET", "/api/settings", token)[0] for _ in range(3)] == [200, 200, 200]
    finally:
        stop_service(process)
