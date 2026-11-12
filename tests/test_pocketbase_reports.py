"""Reports in the PocketBase service: categories, copyright report completeness and the hide-and-notify step."""

import email
import email.policy
import json
import pytest
import socket
import socketserver
import threading
from test_pocketbase_packs import create_pack  # noqa: F401
from test_pocketbase_service import (  # noqa: F401 (the fixtures are used by name)
    admin,
    alice,
    api,
    bob,
    create_level,
    owner,
    pytestmark,
)

COPYRIGHT = {
    "category": "copyright",
    "contactEmail": "rights@example.test",
    "contactAddress": "1 Studio Way, Springfield",
    "contactPhone": "+1 555 0100",
    "work": "The Warehouse level geometry and textures from a commercial skateboarding game",
    "goodFaith": True,
    "accurate": True,
    "fairUseConsidered": True,
    "signature": "Rita Rightsholder",
}


class Sink:
    """A minimal SMTP server that keeps every message it receives."""

    def __init__(self):
        self.messages: list[dict] = []
        sink = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                self.wfile.write(b"220 sink ready\r\n")
                message = {"to": [], "data": ""}
                while line := self.rfile.readline():
                    command = line.decode().strip()
                    verb = command.upper()
                    if verb.startswith(("EHLO", "HELO")):
                        self.wfile.write(b"250 sink\r\n")
                    elif verb.startswith("RCPT TO"):
                        message["to"].append(command.split(":", 1)[1].strip().strip("<>"))
                        self.wfile.write(b"250 ok\r\n")
                    elif verb.startswith(("MAIL FROM", "RSET")):
                        self.wfile.write(b"250 ok\r\n")
                    elif verb == "DATA":
                        self.wfile.write(b"354 go\r\n")
                        body = b""
                        while not body.endswith(b"\r\n.\r\n"):
                            body += self.rfile.readline()
                        message["data"] = body.decode(errors="replace")
                        sink.messages.append(message)
                        message = {"to": [], "data": ""}
                        self.wfile.write(b"250 queued\r\n")
                    elif verb == "QUIT":
                        self.wfile.write(b"221 bye\r\n")
                        return
                    else:
                        self.wfile.write(b"250 ok\r\n")

        self.server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture(scope="module")
def sink(api, admin):
    mail = Sink()
    status, _, body = api.json(
        "PATCH",
        "/api/settings",
        {
            "smtp": {"enabled": True, "host": "127.0.0.1", "port": mail.port, "tls": False},
            "meta": {"senderAddress": "noreply@example.test", "senderName": "Megabonk"},
        },
        admin,
    )
    assert status == 200, body
    yield mail
    mail.close()


def message_text(message: dict) -> str:
    parsed = email.message_from_string(message["data"], policy=email.policy.default)
    return parsed.get_body(preferencelist=("plain",)).get_content()


def report(api, user, target: dict, **fields):
    body = {"user": user["id"], **target, **fields}
    return api.json("POST", "/api/collections/reports/records", body, user["token"])


def copyright_report(api, user, target: dict, item_link: str, **changes):
    return report(api, user, target, **{"itemUrl": item_link, **COPYRIGHT, **changes})


def stored(api, admin, record_id: str) -> dict:
    status, _, body = api.request("GET", f"/api/collections/reports/records/{record_id}", admin)
    assert status == 200, body
    return body


def level_target(level: dict) -> tuple[dict, str]:
    return {"level": level["id"]}, f"https://megabonkmod.party/l/{level['code']}"


def pack_target(pack: dict) -> tuple[dict, str]:
    return {"pack": pack["id"]}, f"https://megabonkmod.party/p/{pack['packId']}"


def is_visible(api, collection: str, record_id: str) -> bool:
    return api.request("GET", f"/api/collections/{collection}/records/{record_id}")[0] == 200


@pytest.mark.parametrize("category", ["broken", "inappropriate", "other"])
def test_a_level_can_be_reported_with_a_category_and_a_reason(api, admin, alice, bob, category):
    level = create_level(api, alice)
    status, _, created = report(api, bob, {"level": level["id"]}, category=category, reason="it is wrong")
    assert status == 200, created
    assert stored(api, admin, created["id"])["status"] == "new"


def test_a_report_without_a_category_is_filed_as_other(api, admin, alice, bob):
    level = create_level(api, alice)
    _, _, created = report(api, bob, {"level": level["id"]}, reason="spam")
    assert stored(api, admin, created["id"])["category"] == "other"


def test_a_non_copyright_report_needs_a_reason(api, alice, bob):
    level = create_level(api, alice)
    assert report(api, bob, {"level": level["id"]}, category="broken")[0] == 400


def test_a_pack_can_be_reported(api, admin, alice, bob):
    pack = create_pack(api, alice)
    status, _, created = report(api, bob, {"pack": pack["id"]}, category="broken", reason="it crashes the game")
    assert status == 200, created
    assert stored(api, admin, created["id"])["pack"] == pack["id"]


def test_a_report_names_exactly_one_item(api, alice, bob):
    level = create_level(api, alice)
    pack = create_pack(api, alice)
    assert report(api, bob, {}, category="other", reason="x")[0] == 400
    assert report(api, bob, {"level": level["id"], "pack": pack["id"]}, category="other", reason="x")[0] == 400


def test_an_unknown_category_is_rejected(api, alice, bob):
    level = create_level(api, alice)
    assert report(api, bob, {"level": level["id"]}, category="mischief", reason="x")[0] == 400


@pytest.mark.parametrize("field,value", [("status", "valid"), ("missing", ["work"]), ("notifiedAt", "2026-01-01 00:00:00.000Z")])
def test_clients_cannot_set_report_server_fields(api, alice, bob, field, value):
    level = create_level(api, alice)
    assert report(api, bob, {"level": level["id"]}, category="other", reason="x", **{field: value})[0] in (400, 403)


@pytest.mark.parametrize("make", [level_target, pack_target], ids=["level", "pack"])
def test_a_complete_copyright_report_is_filed_as_new_with_nothing_missing(api, admin, alice, bob, make):
    item = create_level(api, alice) if make is level_target else create_pack(api, alice)
    target, link = make(item)
    status, _, created = copyright_report(api, bob, target, link)
    assert status == 200, created
    record = stored(api, admin, created["id"])
    assert (record["status"], record["missing"]) == ("new", [])


INCOMPLETE = [
    ("contact", {"contactEmail": "", "contactAddress": "", "contactPhone": ""}),
    ("work", {"work": "  "}),
    ("itemUrl", {"itemUrl": ""}),
    ("goodFaith", {"goodFaith": False}),
    ("accurate", {"accurate": False}),
    ("fairUseConsidered", {"fairUseConsidered": False}),
    ("signature", {"signature": ""}),
]


@pytest.mark.parametrize("missing,changes", INCOMPLETE, ids=[case[0] for case in INCOMPLETE])
def test_an_incomplete_copyright_report_is_kept_but_removes_nothing(api, admin, alice, bob, missing, changes):
    level = create_level(api, alice)
    target, link = level_target(level)
    status, _, created = copyright_report(api, bob, target, link, **changes)
    assert status == 200, created
    record = stored(api, admin, created["id"])
    assert (record["status"], record["missing"]) == ("incomplete", [missing])
    assert is_visible(api, "levels", level["id"])


def test_one_way_of_contact_is_enough(api, admin, alice, bob):
    level = create_level(api, alice)
    target, link = level_target(level)
    _, _, created = copyright_report(api, bob, target, link, contactEmail="", contactAddress="", contactPhone="+1 555 0100")
    assert stored(api, admin, created["id"])["missing"] == []


def test_the_item_link_must_name_the_reported_item(api, admin, alice, bob):
    level = create_level(api, alice)
    other = create_level(api, alice)
    target, _ = level_target(level)
    _, _, created = copyright_report(api, bob, target, f"https://megabonkmod.party/l/{other['code']}")
    assert stored(api, admin, created["id"])["missing"] == ["itemUrl"]
    _, _, created = copyright_report(api, bob, target, "https://example.test/somewhere")
    assert stored(api, admin, created["id"])["missing"] == ["itemUrl"]


def test_a_valid_copyright_report_hides_a_level_and_notifies_the_uploader(api, admin, alice, bob, sink):
    level = create_level(api, alice)
    target, link = level_target(level)
    _, _, created = copyright_report(api, bob, target, link)
    sink.messages.clear()
    status, _, body = api.json("PATCH", f"/api/collections/reports/records/{created['id']}", {"status": "valid"}, admin)
    assert status == 200, body
    assert not is_visible(api, "levels", level["id"])
    assert body["notifiedAt"]
    (message,) = sink.messages
    assert any("alice" in address for address in message["to"])
    text = message_text(message)
    assert COPYRIGHT["work"] in text
    assert "Rita Rightsholder" in text and "rights@example.test" in text
    assert COPYRIGHT["contactAddress"] not in text and COPYRIGHT["contactPhone"] not in text


def test_a_valid_copyright_report_hides_a_pack(api, admin, alice, bob, sink):
    pack = create_pack(api, alice)
    target, link = pack_target(pack)
    _, _, created = copyright_report(api, bob, target, link)
    status, _, body = api.json("PATCH", f"/api/collections/reports/records/{created['id']}", {"status": "valid"}, admin)
    assert status == 200, body
    assert not is_visible(api, "packs", pack["id"])


def test_an_incomplete_report_cannot_be_made_valid(api, admin, alice, bob):
    level = create_level(api, alice)
    target, link = level_target(level)
    _, _, created = copyright_report(api, bob, target, link, signature="")
    status, _, body = api.json("PATCH", f"/api/collections/reports/records/{created['id']}", {"status": "valid"}, admin)
    assert status == 400, body
    assert "signature" in json.dumps(body).lower()
    assert is_visible(api, "levels", level["id"])
    assert stored(api, admin, created["id"])["status"] == "incomplete"


def test_completing_a_report_in_the_dashboard_clears_the_missing_list(api, admin, alice, bob):
    level = create_level(api, alice)
    target, link = level_target(level)
    _, _, created = copyright_report(api, bob, target, link, signature="")
    api.json(
        "PATCH",
        f"/api/collections/reports/records/{created['id']}",
        {"signature": "Rita Rightsholder", "status": "needs-info"},
        admin,
    )
    record = stored(api, admin, created["id"])
    assert (record["missing"], record["status"]) == ([], "needs-info")
    status, _, body = api.json("PATCH", f"/api/collections/reports/records/{created['id']}", {"status": "valid"}, admin)
    assert status == 200, body


@pytest.mark.parametrize("status", ["needs-info", "rejected"])
def test_asking_for_information_or_rejecting_a_report_removes_nothing(api, admin, alice, bob, status):
    level = create_level(api, alice)
    target, link = level_target(level)
    _, _, created = copyright_report(api, bob, target, link)
    code, _, body = api.json("PATCH", f"/api/collections/reports/records/{created['id']}", {"status": status}, admin)
    assert code == 200, body
    assert is_visible(api, "levels", level["id"])
    assert not body["notifiedAt"]


def test_making_a_report_valid_twice_notifies_once(api, admin, alice, bob, sink):
    level = create_level(api, alice)
    target, link = level_target(level)
    _, _, created = copyright_report(api, bob, target, link)
    sink.messages.clear()
    api.json("PATCH", f"/api/collections/reports/records/{created['id']}", {"status": "valid"}, admin)
    api.json("PATCH", f"/api/collections/reports/records/{created['id']}", {"status": "valid", "reason": "more"}, admin)
    assert len(sink.messages) == 1


def test_a_valid_non_copyright_report_hides_the_item_without_naming_the_reporter(api, admin, alice, bob, sink):
    level = create_level(api, alice)
    _, _, created = report(api, bob, {"level": level["id"]}, category="inappropriate", reason="offensive title")
    sink.messages.clear()
    api.json("PATCH", f"/api/collections/reports/records/{created['id']}", {"status": "valid"}, admin)
    assert not is_visible(api, "levels", level["id"])
    (message,) = sink.messages
    assert "offensive title" in message_text(message)
    assert "bob" not in message_text(message).lower()


def test_reporters_cannot_read_or_change_reports(api, admin, alice, bob):
    level = create_level(api, alice)
    _, _, created = report(api, bob, {"level": level["id"]}, category="other", reason="x")
    url = f"/api/collections/reports/records/{created['id']}"
    assert api.request("GET", url, bob["token"])[0] in (403, 404)
    assert api.json("PATCH", url, {"status": "valid"}, bob["token"])[0] in (403, 404)


def test_deleting_a_reported_pack_removes_its_reports(api, admin, alice, bob):
    pack = create_pack(api, alice)
    _, _, created = report(api, bob, {"pack": pack["id"]}, category="other", reason="x")
    assert api.request("DELETE", f"/api/collections/packs/records/{pack['id']}", alice["token"])[0] == 204
    assert api.request("GET", f"/api/collections/reports/records/{created['id']}", admin)[0] == 404
