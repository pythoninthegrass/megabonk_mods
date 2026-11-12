"""Response security headers the PocketBase service adds on top of its built-in ones."""

import pytest
from test_pocketbase_service import api, pytestmark  # noqa: F401 (the fixtures are used by name)

EXPECTED = {
    "strict-transport-security": "max-age=63072000; includeSubDomains",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "cross-origin-resource-policy": "same-site",
}


@pytest.mark.parametrize("path", ["/api/health", "/api/no-such-route"])
def test_api_responses_carry_the_security_headers(api, path):
    _, headers, _ = api.request("GET", path)
    for name, value in EXPECTED.items():
        assert headers.get(name) == value, name


def test_api_responses_keep_the_built_in_protections(api):
    _, headers, _ = api.request("GET", "/api/health")
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("cross-origin-opener-policy") == "same-origin"
