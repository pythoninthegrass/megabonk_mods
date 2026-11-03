"""Hardened HTTPS fetch for the vendored archives, shared by the packaging scripts.

A downloaded archive that turns out to be a 404 page or a captive-portal login must read
as a missing asset, never as a checksum mismatch, so the status is checked before the body
is touched, redirects stay on the original host, and TLS has a floor.
"""

from __future__ import annotations

import hashlib
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "megabonk-levels-package-builder"
DEFAULT_TIMEOUT = 600.0
MAX_BYTES = 400 * 1024 * 1024
MAX_REDIRECTS = 5
CHUNK_BYTES = 1024 * 1024
REDIRECT_CODES = (301, 302, 303, 307, 308)
PAGE_TYPES = ("text/html", "application/xhtml+xml", "text/plain")

# The CDNs a known asset host legitimately hands off to. Anything else off-host is refused.
ALLOWED_HOPS = {
    "github.com": ("githubusercontent.com",),
    "dotnetcli.azureedge.net": ("azureedge.net", "microsoft.com"),
    "dotnet.microsoft.com": ("azureedge.net", "microsoft.com"),
}


class MissingAsset(Exception):
    """The asset is not at that URL: a 404, a login page, a redirect off-host."""


class DownloadError(Exception):
    """The host, the connection, or the bytes delivered were not usable."""


def allowed_hosts_for(url: str) -> tuple[str, ...]:
    """Domains a redirect may land on besides the original host, matched on subdomains."""
    return ALLOWED_HOPS.get(_host(url)[0], ())


def tls_context() -> ssl.SSLContext:
    """A verifying context with TLS 1.2 as the floor: older handshakes are refused."""
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context


class _RefuseRedirects(urllib.request.HTTPRedirectHandler):
    """Redirects are followed by download() so each hop can be checked against the host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001 - urllib's signature
        return None


def default_opener(context: ssl.SSLContext | None = None) -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=context or tls_context()),
        _RefuseRedirects(),
    )


def download(
    url: str,
    *,
    opener: urllib.request.OpenerDirector | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_bytes: int = MAX_BYTES,
    allowed_hosts: tuple[str, ...] | None = None,
) -> bytes:
    """Fetch url in full, or say why the asset is not there. Nothing is written by this call."""
    active = opener if opener is not None else default_opener()
    _require_https(url)
    hops = allowed_hosts if allowed_hosts is not None else allowed_hosts_for(url)
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        response = _exchange(active, current, timeout)
        try:
            status = _status(response)
            if status in REDIRECT_CODES:
                current = _stay_on_host(url, current, _header(response, "Location"), hops)
                continue
            if status != 200:
                raise MissingAsset(f"{url} returned HTTP {status}: the asset is not there")
            _reject_page(url, response)
            return _read_body(url, response, max_bytes)
        finally:
            _close(response)
    raise DownloadError(f"{url} redirected more than {MAX_REDIRECTS} times")


def download_to(
    url: str,
    destination: Path,
    *,
    opener: urllib.request.OpenerDirector | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_bytes: int = MAX_BYTES,
    expected_sha256: str | None = None,
    allowed_hosts: tuple[str, ...] | None = None,
) -> Path:
    """Cache url at destination, verified first, so a bad response never lands in the cache."""
    target = Path(destination)
    if target.is_file():
        return target
    body = download(url, opener=opener, timeout=timeout, max_bytes=max_bytes, allowed_hosts=allowed_hosts)
    digest = hashlib.sha256(body).hexdigest()
    if expected_sha256 and digest != expected_sha256.lower():
        raise DownloadError(
            f"{url} has sha256 {digest}, expected {expected_sha256}: what is served there is "
            "not the archived asset the manifest names"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".part")
    temporary.write_bytes(body)
    os.replace(temporary, target)
    return target


def _require_https(url: str) -> None:
    if urllib.parse.urlsplit(url).scheme != "https":
        raise DownloadError(f"refusing to fetch {url}: only https downloads are allowed")
    try:
        host = _host(url)
    except ValueError as exc:
        raise DownloadError(f"{url} is not a usable URL: {exc}") from exc
    if not host[0]:
        raise DownloadError(f"{url} names no host to connect to")


def _exchange(opener: urllib.request.OpenerDirector, url: str, timeout: float):
    """One GET. Redirects and HTTP errors come back as HTTPError, which carries code and headers."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        return opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        return exc
    except ssl.SSLError as exc:
        raise DownloadError(f"{url}: the TLS handshake failed: {exc}") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLError):
            raise DownloadError(f"{url}: the TLS handshake failed: {exc.reason}") from exc
        raise DownloadError(f"{url} could not be reached: {exc.reason}") from exc
    except OSError as exc:
        raise DownloadError(f"{url} could not be reached: {exc}") from exc


def _status(response) -> int:
    return getattr(response, "status", None) or response.getcode()


def _header(response, name: str) -> str | None:
    headers = getattr(response, "headers", None)
    return headers.get(name) if headers is not None else None


def _reject_page(url: str, response) -> None:
    content_type = (_header(response, "Content-Type") or "").split(";")[0].strip().lower()
    if content_type in PAGE_TYPES:
        raise MissingAsset(
            f"{url} served {content_type}, which is a login or captive-portal page rather than the archive"
        )


def _read_body(url: str, response, max_bytes: int) -> bytes:
    declared = _header(response, "Content-Length")
    if declared and declared.isdigit() and int(declared) > max_bytes:
        raise DownloadError(f"{url} says it is {declared} bytes, larger than the {max_bytes} byte limit")
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise DownloadError(f"{url} is larger than the {max_bytes} byte limit")
        chunks.append(chunk)
    body = b"".join(chunks)
    if not body:
        raise MissingAsset(f"{url} returned an empty body: the asset is not there")
    return body


def _stay_on_host(original: str, current: str, location: str | None, allowed_hosts: tuple[str, ...]) -> str:
    if not location:
        raise MissingAsset(f"{original} redirected without saying where to")
    target = urllib.parse.urljoin(current, location)
    if urllib.parse.urlsplit(target).scheme != "https":
        raise MissingAsset(f"{original} redirects to {target}: only https downloads are allowed")
    try:
        hop = _host(target)
    except ValueError as exc:
        raise MissingAsset(f"{original} redirects to {target}, which is not a usable URL: {exc}") from exc
    if hop != _host(original) and not _allowed_host(hop[0], allowed_hosts):
        raise MissingAsset(
            f"{original} redirects to {target} on a different host: the download stays on {_host(original)[0]}"
        )
    return target


def _allowed_host(host: str, allowed_hosts: tuple[str, ...]) -> bool:
    return any(host == entry or host.endswith("." + entry) for entry in allowed_hosts)


def _host(url: str) -> tuple[str, int]:
    parts = urllib.parse.urlsplit(url)
    return (parts.hostname or "").lower(), parts.port or 443


def _close(response) -> None:
    try:
        response.close()
    except Exception:  # noqa: BLE001 - a failed close must not replace the real outcome
        pass
