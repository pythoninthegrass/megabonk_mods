"""Submit a macOS player package zip to Apple's notary service and wait for the verdict."""

from __future__ import annotations

import argparse
import base64
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path

MISSING_CREDENTIALS = (
    "No notarization credentials: set NOTARY_PROFILE to a notarytool keychain profile, "
    "or APPLE_API_KEY, APPLE_API_ISSUER and APPLE_API_KEY_B64 for an App Store Connect API key."
)


class NotarizeError(Exception):
    pass


def run_command(argv: list[str]) -> int:
    return subprocess.run(argv, check=False).returncode


def submit(zip_path: Path, env: Mapping[str, str], runner: Callable[[list[str]], int] = run_command) -> int:
    """Run notarytool on the zip and return its exit code; the API key file never outlives the call."""
    base = ["xcrun", "notarytool", "submit", str(zip_path)]
    if env.get("NOTARY_PROFILE"):
        return runner([*base, "--keychain-profile", env["NOTARY_PROFILE"], "--wait"])
    if not all(env.get(name) for name in ("APPLE_API_KEY", "APPLE_API_ISSUER", "APPLE_API_KEY_B64")):
        raise NotarizeError(MISSING_CREDENTIALS)
    descriptor, name = tempfile.mkstemp(suffix=".p8")
    key_path = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(base64.b64decode(env["APPLE_API_KEY_B64"]))
        key_path.chmod(0o600)
        argv = [*base, "--key", str(key_path), "--key-id", env["APPLE_API_KEY"], "--issuer", env["APPLE_API_ISSUER"], "--wait"]
        return runner(argv)
    finally:
        key_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip", type=Path, help="The package zip to submit.")
    args = parser.parse_args(argv)
    try:
        return submit(args.zip, os.environ)
    except NotarizeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
