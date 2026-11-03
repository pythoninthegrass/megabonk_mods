"""The vendor-cache download: status before body, host pinned, TLS floored."""

from __future__ import annotations

import asset_download
import email.message
import hashlib
import io
import pytest
import ssl
import urllib.error
import urllib.request
from pathlib import Path

URL = "https://example.test/MelonLoader.x64.zip"
ARCHIVE = b"PK\x03\x04archive-bytes"


def _digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


class RecordingBytesIO(io.BytesIO):
    """A response body that says whether anyone read it."""

    def __init__(self, body: bytes) -> None:
        super().__init__(body)
        self.reads = 0

    def read(self, size: int = -1) -> bytes:
        self.reads += 1
        return super().read(size)


def http_error(
    code: int, location: str | None = None, body: bytes = b"<html>sign in</html>"
) -> urllib.error.HTTPError:
    headers = email.message.Message()
    if location:
        headers["Location"] = location
    return urllib.error.HTTPError(URL, code, f"HTTP {code}", headers, RecordingBytesIO(body))


class FakeResponse:
    """The 200 branch of an opener: reports status and headers, hands out the body on read."""

    def __init__(
        self,
        body: bytes = ARCHIVE,
        status: int = 200,
        content_type: str | None = "application/zip",
        content_length: int | None = None,
    ) -> None:
        self.body = body
        self.status = status
        self.headers = email.message.Message()
        if content_type is not None:
            self.headers["Content-Type"] = content_type
        self.headers["Content-Length"] = str(len(body) if content_length is None else content_length)
        self.reads = 0
        self.closed = 0
        self._position = 0

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *exc: object) -> bool:
        self.close()
        return False

    def close(self) -> None:
        self.closed += 1

    def read(self, size: int = -1) -> bytes:
        self.reads += 1
        chunk = self.body[self._position : self._position + (size if size and size > 0 else len(self.body))]
        self._position += len(chunk)
        return chunk


class FakeOpener:
    """An opener that answers with prepared responses or raises prepared exceptions."""

    def __init__(self, *outcomes: object) -> None:
        self.outcomes = list(outcomes)
        self.urls: list[str] = []
        self.timeouts: list[object] = []
        self.agents: list[str | None] = []

    def open(self, request: urllib.request.Request, timeout: object = None) -> object:
        self.urls.append(request.full_url)
        self.timeouts.append(timeout)
        self.agents.append(request.get_header("User-agent"))
        if not self.outcomes:
            raise AssertionError(f"unexpected request for {request.full_url}")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def test_a_good_download_returns_the_body() -> None:
    opener = FakeOpener(FakeResponse())
    assert asset_download.download(URL, opener=opener) == ARCHIVE


def test_the_request_names_the_builder_user_agent() -> None:
    opener = FakeOpener(FakeResponse())
    asset_download.download(URL, opener=opener)
    assert asset_download.USER_AGENT in opener.agents[0]


def test_the_timeout_reaches_the_opener() -> None:
    opener = FakeOpener(FakeResponse())
    asset_download.download(URL, opener=opener, timeout=7.5)
    assert opener.timeouts == [7.5]


def test_a_404_reads_as_a_missing_asset() -> None:
    error = http_error(404)
    opener = FakeOpener(error)
    with pytest.raises(asset_download.MissingAsset, match="404"):
        asset_download.download(URL, opener=opener)
    assert error.fp.reads == 0, "the error page must never be read as the asset"


def test_a_non_200_status_never_reads_the_body() -> None:
    response = FakeResponse(body=b"<html>sign in</html>", status=403, content_type="text/html")
    opener = FakeOpener(response)
    with pytest.raises(asset_download.MissingAsset, match="403"):
        asset_download.download(URL, opener=opener)
    assert response.reads == 0


def test_a_captive_portal_page_reads_as_a_missing_asset() -> None:
    opener = FakeOpener(FakeResponse(body=b"<html><body>wifi login</body></html>", content_type="text/html"))
    with pytest.raises(asset_download.MissingAsset, match="portal") as caught:
        asset_download.download(URL, opener=opener)
    assert "sha256" not in str(caught.value)


def test_plain_text_is_read_as_a_page_rather_than_an_archive() -> None:
    opener = FakeOpener(FakeResponse(body=b"404 Not Found", content_type="text/plain"))
    with pytest.raises(asset_download.MissingAsset, match="portal"):
        asset_download.download(URL, opener=opener)


def test_an_empty_body_reads_as_a_missing_asset() -> None:
    opener = FakeOpener(FakeResponse(body=b""))
    with pytest.raises(asset_download.MissingAsset, match="empty"):
        asset_download.download(URL, opener=opener)


def test_an_oversized_content_length_is_refused_before_the_body_is_read() -> None:
    response = FakeResponse(content_length=asset_download.MAX_BYTES + 1)
    opener = FakeOpener(response)
    with pytest.raises(asset_download.DownloadError, match="larger than"):
        asset_download.download(URL, opener=opener)
    assert response.reads == 0


def test_a_body_oversized_without_a_content_length_is_refused_while_reading() -> None:
    response = FakeResponse(body=b"x" * (asset_download.MAX_BYTES + 1))
    del response.headers["Content-Length"]
    opener = FakeOpener(response)
    with pytest.raises(asset_download.DownloadError, match="larger than"):
        asset_download.download(URL, opener=opener, max_bytes=1024)


def test_a_plain_http_url_is_refused_before_any_request() -> None:
    opener = FakeOpener()
    with pytest.raises(asset_download.DownloadError, match="https"):
        asset_download.download("http://example.test/MelonLoader.x64.zip", opener=opener)
    assert opener.urls == []


def test_a_redirect_to_another_host_is_refused() -> None:
    opener = FakeOpener(http_error(302, location="https://evil.test/MelonLoader.x64.zip"))
    with pytest.raises(asset_download.MissingAsset, match="different host"):
        asset_download.download(URL, opener=opener)
    assert opener.urls == [URL]


def test_a_redirect_through_plain_http_is_refused() -> None:
    opener = FakeOpener(http_error(302, location="http://example.test/MelonLoader.x64.zip"))
    with pytest.raises(asset_download.MissingAsset, match="https"):
        asset_download.download(URL, opener=opener)
    assert opener.urls == [URL]


def test_a_redirect_to_the_same_host_is_followed() -> None:
    opener = FakeOpener(
        http_error(302, location="/mirror/MelonLoader.x64.zip"),
        FakeResponse(),
    )
    assert asset_download.download(URL, opener=opener) == ARCHIVE
    assert opener.urls == [URL, "https://example.test/mirror/MelonLoader.x64.zip"]


def test_a_redirect_to_a_listed_cdn_is_followed() -> None:
    url = "https://github.com/LavaGang/MelonLoader/releases/download/v0.7.3/MelonLoader.x64.zip"
    opener = FakeOpener(
        http_error(302, location="https://release-assets.githubusercontent.com/github-production-release-asset/1"),
        FakeResponse(),
    )
    assert asset_download.download(url, opener=opener) == ARCHIVE
    assert len(opener.urls) == 2


def test_an_explicit_allow_list_opens_a_cdn_for_an_unknown_host() -> None:
    opener = FakeOpener(http_error(302, location="https://cdn.example.org/x.zip"), FakeResponse())
    assert asset_download.download(URL, opener=opener, allowed_hosts=("example.org",)) == ARCHIVE


def test_a_lookalike_of_an_allowed_cdn_is_still_refused() -> None:
    opener = FakeOpener(http_error(302, location="https://evil-githubusercontent.com/x.zip"))
    with pytest.raises(asset_download.MissingAsset, match="different host"):
        asset_download.download(URL, opener=opener, allowed_hosts=("githubusercontent.com",))


def test_the_github_release_host_may_hand_off_to_its_asset_cdn() -> None:
    url = "https://github.com/LavaGang/MelonLoader/releases/download/v0.7.3/MelonLoader.x64.zip"
    assert "githubusercontent.com" in asset_download.allowed_hosts_for(url)


def test_the_dotnet_cli_host_may_hand_off_to_its_cdn() -> None:
    url = "https://dotnetcli.azureedge.net/dotnet/Runtime/6.0.36/dotnet-runtime-6.0.36-win-x64.zip"
    assert asset_download.allowed_hosts_for(url) == ("azureedge.net", "microsoft.com")


def test_an_unexpected_host_has_no_redirect_allowance() -> None:
    assert asset_download.allowed_hosts_for(URL) == ()


def test_a_redirect_chain_that_never_ends_is_refused() -> None:
    hops = [http_error(302, location=f"/hop{index}") for index in range(asset_download.MAX_REDIRECTS + 2)]
    opener = FakeOpener(*hops)
    with pytest.raises(asset_download.DownloadError, match="redirect"):
        asset_download.download(URL, opener=opener)


def test_the_default_opener_requires_tls_1_2_and_a_trusted_certificate() -> None:
    handlers = [h for h in asset_download.default_opener().handlers if isinstance(h, urllib.request.HTTPSHandler)]
    assert len(handlers) == 1, "the opener must answer https with the pinned context"
    context = handlers[0]._context
    assert context.minimum_version is ssl.TLSVersion.TLSv1_2
    assert context.check_hostname and context.verify_mode is ssl.CERT_REQUIRED


def test_a_tls_failure_names_tls() -> None:
    opener = FakeOpener(ssl.SSLError("sslv3 alert handshake failure"))
    with pytest.raises(asset_download.DownloadError, match="TLS"):
        asset_download.download(URL, opener=opener)


def test_a_connection_failure_names_the_url() -> None:
    opener = FakeOpener(urllib.error.URLError("Name or service not known"))
    with pytest.raises(asset_download.DownloadError, match="example.test"):
        asset_download.download(URL, opener=opener)


def test_download_to_saves_a_verified_archive(tmp_path: Path) -> None:
    opener = FakeOpener(FakeResponse())
    target = tmp_path / "cache" / "MelonLoader.x64.zip"
    got = asset_download.download_to(URL, target, opener=opener, expected_sha256=_digest(ARCHIVE))
    assert got == target
    assert target.read_bytes() == ARCHIVE


def test_an_existing_cache_is_never_fetched(tmp_path: Path) -> None:
    target = tmp_path / "cache" / "MelonLoader.x64.zip"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"cached")
    opener = FakeOpener()
    assert asset_download.download_to(URL, target, opener=opener) == target
    assert opener.urls == []


def test_a_download_that_does_not_match_its_digest_never_reaches_the_cache(tmp_path: Path) -> None:
    opener = FakeOpener(FakeResponse())
    target = tmp_path / "cache" / "MelonLoader.x64.zip"
    with pytest.raises(asset_download.DownloadError, match="sha256"):
        asset_download.download_to(URL, target, opener=opener, expected_sha256=_digest(b"something else"))
    assert not target.exists()
    assert not (target.parent / (target.name + ".part")).exists()


def test_a_404_leaves_nothing_in_the_cache(tmp_path: Path) -> None:
    opener = FakeOpener(http_error(404))
    target = tmp_path / "cache" / "MelonLoader.x64.zip"
    with pytest.raises(asset_download.MissingAsset, match="404"):
        asset_download.download_to(URL, target, opener=opener, expected_sha256=_digest(ARCHIVE))
    assert not target.exists()
    assert not target.parent.exists() or list(target.parent.iterdir()) == []


def test_only_the_hardened_fetcher_touches_the_network() -> None:
    scripts = Path(asset_download.__file__).parent
    offenders = sorted(
        path.name
        for path in scripts.rglob("*.py")
        if path.name != "asset_download.py" and "urlopen" in path.read_text(encoding="utf-8")
    )
    assert offenders == []


def _digest(body: bytes) -> str:
    import hashlib

    return hashlib.sha256(body).hexdigest()
